from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        chunks = self.store.search(question, top_k)
        if not chunks:
            return "Không tìm thấy thông tin phù hợp trong cơ sở kiến thức."

        context = "\n\n".join(
            f"[{index}] {chunk['content']}"
            for index, chunk in enumerate(chunks, start=1)
        )
        prompt = f"""Dựa trên context dưới đây, hãy trả lời câu hỏi của người dùng.
Chỉ sử dụng thông tin có trong context. Nếu context không đủ để trả lời,
hãy nói rõ là không tìm thấy thông tin. Khi có thể, hãy trích dẫn nguồn
bằng các số thứ tự như [1], [2].

Context:
{context}

Câu hỏi: {question}

Trả lời:"""
        return self.llm_fn(prompt)
