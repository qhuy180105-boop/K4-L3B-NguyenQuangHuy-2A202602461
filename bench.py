"""Run the shared Shopee buyer-policy retrieval benchmark.

Only the body of each Markdown file is embedded. Select a chunker with
``--chunker`` when comparing strategies with teammates.

Usage:
    # Set GEMINI_API_KEY in .env, then run a semantic benchmark:
    python bench.py
    python bench.py --chunker fixed --output ket_qua_benchmark_fixed.txt
    python bench.py --chunker sentence --output ket_qua_benchmark_sentence.txt
    # Mock is available only for a no-network smoke test:
    python bench.py --embedding-provider mock
    python bench.py --data-dir data/shopee-buyer-policy --output ket_qua_benchmark.txt
"""

from __future__ import annotations

import argparse
import ast
import os
import re
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        """Allow explicit environment variables when python-dotenv is unavailable."""
        return False

from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import GEMINI_EMBEDDING_MODEL, GeminiEmbedder, _mock_embed
from src.models import Document
from src.store import EmbeddingStore


DATA_DIR = Path("data/shopee-buyer-policy")
OUTPUT_FILE = Path("ket_qua_benchmark.txt")

# Default strategy. The CLI can replace it while keeping corpus and BENCHMARKS
# identical, making comparisons fair.
CHUNKER = RecursiveChunker(chunk_size=700)

# These five questions are checked against the Shopee buyer-policy corpus.
# The last one is deliberately run both without and with its buyer filter.
BENCHMARKS = [
    {
        "question": "Người mua gửi yêu cầu Trả hàng/Hoàn tiền trực tiếp tại trang đơn hàng như thế nào?",
        "gold_answer": "Vào Tôi > Chờ giao hàng hoặc Đã giao, chọn đơn hàng và bấm Trả hàng/Hoàn tiền.",
    },
    {
        "question": "Yêu cầu Trả hàng/Hoàn tiền thường được xử lý trong bao lâu và tiền hoàn được nhận sau bao lâu nếu yêu cầu được chấp nhận?",
        "gold_answer": "Yêu cầu thường được xử lý trong 3-5 ngày làm việc; tiền hoàn về trong 1-14 ngày làm việc tùy phương thức thanh toán.",
    },
    {
        "question": "Người mua có thể yêu cầu hủy đơn ở những trạng thái nào?",
        "gold_answer": "Chờ xác nhận được hủy ngay; Chờ lấy hàng cần chờ phản hồi Người bán; các trạng thái khác không thể yêu cầu hủy.",
    },
    {
        "question": "Nếu Shipper không liên hệ nhưng cập nhật giao hàng không thành công, Người mua cần làm gì?",
        "gold_answer": "Chờ cuộc gọi tiếp theo từ Shipper; Shipper sẽ có 3 lần liên hệ để giao hàng theo thời gian dự kiến.",
    },
    {
        "question": "Nếu quá 24 giờ đơn bị cập nhật đã giao nhưng Người mua chưa nhận được hàng, cần chọn lý do Trả hàng/Hoàn tiền nào và có cần bằng chứng không?",
        "gold_answer": "Chọn lý do Chưa nhận được hàng; không cần cung cấp bằng chứng.",
        "metadata_filter": {"audience": "buyer"},
    },
]


def _parse_scalar(value: str) -> Any:
    """Parse the scalar YAML values used by this project's frontmatter."""
    value = value.strip()
    if not value:
        return ""
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value.split(" #", 1)[0].strip()


def split_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    """Return frontmatter metadata and body, without requiring PyYAML."""
    if not markdown.startswith("---"):
        return {}, markdown

    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)(.*)$", markdown, flags=re.DOTALL)
    if not match:
        return {}, markdown

    metadata: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = _parse_scalar(value)
    return metadata, match.group(2).strip()


def load_chunk_documents(data_dir: Path) -> list[Document]:
    """Read Markdown, strip frontmatter, and turn body chunks into Documents."""
    documents: list[Document] = []
    for path in sorted(data_dir.rglob("*.md")):
        frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
        for index, chunk in enumerate(CHUNKER.chunk(body)):
            content = chunk.strip()
            if not content:
                continue
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=content,
                    # doc_id identifies the source file; Document.id identifies a chunk.
                    metadata={**frontmatter, "doc_id": path.stem, "source": str(path)},
                )
            )
    return documents


def extractive_llm(prompt: str) -> str:
    """Offline deterministic LLM substitute so the benchmark is runnable by default."""
    context = prompt.partition("Context:\n")[2].partition("\n\nCâu hỏi:")[0]
    text = re.sub(r"^\[\d+\]\s*", "", context, flags=re.MULTILINE)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    answer = " ".join(sentence for sentence in sentences[:3] if sentence)
    return answer or "Không tìm thấy thông tin phù hợp trong các chunk đã truy xuất."


def format_results(results: list[dict[str, Any]]) -> list[str]:
    if not results:
        return ["  (Không có chunk phù hợp.)"]
    lines: list[str] = []
    for rank, result in enumerate(results, start=1):
        doc_id = result["metadata"].get("doc_id", "unknown")
        preview = " ".join(result["content"].split())[:280]
        lines.extend(
            [
                f"  {rank}. score={result['score']:.4f} doc_id={doc_id}",
                f"     {preview}",
            ]
        )
    return lines


def describe_chunker(chunker: object) -> str:
    """Format settings without assuming all chunkers share the same attributes."""
    if isinstance(chunker, SentenceChunker):
        return f"{chunker.__class__.__name__} (max_sentences_per_chunk={chunker.max_sentences_per_chunk})"
    if isinstance(chunker, FixedSizeChunker):
        return f"{chunker.__class__.__name__} (chunk_size={chunker.chunk_size}, overlap={chunker.overlap})"
    return f"{chunker.__class__.__name__} (chunk_size={chunker.chunk_size})"


def get_embedding_fn(provider: str):
    """Return the requested embedding backend; mock must be explicitly chosen."""
    if provider == "gemini":
        try:
            return GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
        except (ImportError, RuntimeError) as exc:
            raise RuntimeError(
                "Gemini embedding requires `python -m pip install google-genai` and "
                "GEMINI_API_KEY in .env (or the environment). For a non-semantic local "
                "smoke test only, run with --embedding-provider mock."
            ) from exc
    if provider == "mock":
        return _mock_embed
    raise ValueError(f"Unsupported embedding provider: {provider}")


def build_chunker(strategy: str):
    """Use consistent, named chunking configurations for benchmark comparisons."""
    if strategy == "recursive":
        return RecursiveChunker(chunk_size=700)
    if strategy == "fixed":
        return FixedSizeChunker(chunk_size=700, overlap=70)
    if strategy == "sentence":
        return SentenceChunker(max_sentences_per_chunk=3)
    raise ValueError(f"Unsupported chunking strategy: {strategy}")


def run_benchmark(data_dir: Path, output_file: Path, embedding_provider: str) -> str:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {data_dir}")

    docs = load_chunk_documents(data_dir)
    if not docs:
        raise RuntimeError(f"No non-empty Markdown chunks found in {data_dir}")

    embedding_fn = get_embedding_fn(embedding_provider)
    store = EmbeddingStore(collection_name="shopee_buyer_policy_benchmark", embedding_fn=embedding_fn)
    store.add_documents(docs)
    agent = KnowledgeBaseAgent(store=store, llm_fn=extractive_llm)

    lines = [
        "SHOPEE BUYER-POLICY BENCHMARK",
        f"Corpus: {data_dir}",
        f"Chunker: {describe_chunker(CHUNKER)}",
        f"Embedding backend: {getattr(embedding_fn, '_backend_name', embedding_provider)}",
        f"Chunks loaded: {store.get_collection_size()}",
        "",
    ]
    for number, benchmark in enumerate(BENCHMARKS, start=1):
        question = benchmark["question"]
        lines.extend([f"{'=' * 72}\nQuestion {number}: {question}", f"Gold answer: {benchmark['gold_answer']}"])

        # Every benchmark uses the unfiltered baseline search.
        lines.append("\nsearch(...), top-3:")
        lines.extend(format_results(store.search(question, top_k=3)))

        # The designated question proves the A/B metadata-filter workflow.
        metadata_filter = benchmark.get("metadata_filter")
        if metadata_filter:
            lines.append(f"\nsearch_with_filter(..., metadata_filter={metadata_filter}), top-3:")
            filtered = store.search_with_filter(question, top_k=3, metadata_filter=metadata_filter)
            lines.extend(format_results(filtered))
            if not filtered:
                lines.append(
                    "  WARNING: no corpus chunk has this metadata value; normalize "
                    "frontmatter audience values before treating this A/B result as meaningful."
                )

        lines.extend(["\nAgent answer:", agent.answer(question, top_k=3), ""])

    report = "\n".join(lines)
    output_file.write_text(report + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark chunk retrieval on Markdown frontmatter corpora.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Directory containing .md corpus files.")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="Text file to write benchmark results to.")
    parser.add_argument(
        "--embedding-provider",
        choices=("gemini", "mock"),
        default=os.getenv("BENCH_EMBEDDING_PROVIDER", "gemini").strip().lower(),
        help="Embedding backend. Defaults to BENCH_EMBEDDING_PROVIDER or Gemini; mock is only for smoke tests.",
    )
    parser.add_argument(
        "--chunker",
        choices=("recursive", "fixed", "sentence"),
        default="recursive",
        help="Chunking strategy; default recursive uses a 700-character limit.",
    )
    return parser.parse_args()


def main() -> int:
    global CHUNKER
    load_dotenv(override=False)
    args = parse_args()
    CHUNKER = build_chunker(args.chunker)
    report = run_benchmark(args.data_dir, args.output, args.embedding_provider)
    print(report)
    print(f"Saved benchmark results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
