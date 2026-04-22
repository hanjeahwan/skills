#!/usr/bin/env python3
"""Compatibility wrapper for the synthetic retrieval benchmark suite."""

from __future__ import annotations

import sys

from run_retrieval_benchmarks import main as run_retrieval_benchmarks_main


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--suite", "synthetic", "--json", *sys.argv[1:]]
    run_retrieval_benchmarks_main()
