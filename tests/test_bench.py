"""Regression tests for the submitted buyer-policy benchmark."""

from __future__ import annotations

import builtins
import importlib.util
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BENCH_PATH = REPOSITORY_ROOT / "bench.py"
BUYER_DATA_DIR = REPOSITORY_ROOT / "data" / "shopee-buyer-policy"


def load_bench_module(module_name: str = "bench"):
    spec = importlib.util.spec_from_file_location(module_name, BENCH_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load bench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBuyerPolicyBenchmark(unittest.TestCase):
    def test_benchmark_report_identifies_buyer_corpus_and_uses_buyer_filter(self) -> None:
        """The CLI default must load the submitted buyer corpus, not a caller-supplied path."""
        bench = load_bench_module()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "benchmark.txt"
            with patch.object(
                sys,
                "argv",
                ["bench.py", "--embedding-provider", "mock", "--output", str(output)],
            ):
                self.assertEqual(bench.main(), 0)
            report = output.read_text(encoding="utf-8")

        self.assertIn("SHOPEE BUYER-POLICY BENCHMARK", report)
        self.assertIn("metadata_filter={'audience': 'buyer'}", report)
        self.assertNotIn("MIT FINANCIAL-AID BENCHMARK", report)

    def test_mock_benchmark_module_imports_without_python_dotenv(self) -> None:
        """A missing optional .env loader must not prevent a mock-only benchmark from starting."""
        real_import = builtins.__import__

        def import_without_dotenv(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "dotenv":
                raise ModuleNotFoundError("No module named 'dotenv'")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=import_without_dotenv):
            bench = load_bench_module("bench_without_dotenv")

        self.assertFalse(bench.load_dotenv())


if __name__ == "__main__":
    unittest.main()
