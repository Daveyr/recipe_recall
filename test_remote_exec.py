#!/usr/bin/env python3
"""Run the local scraper in a way similar to how an MCP tool would.

This helper repeatedly invokes `bbcgoodfood_scraper_yolo.py` using the same
Python interpreter (`sys.executable`). It supports two capture modes:
- `pipe`: capture stdout/stderr via subprocess pipes (quick test)
- `tempfile`: write stdout/stderr to a temporary file and read it back

Use this script to reproduce timeouts, inspect combined output, and test
different timeout/retry settings before running under an MCP server.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import subprocess
import tempfile
import time
from typing import Tuple


def run_with_tempfile(cmd: list[str], timeout: float) -> Tuple[int, str, bool]:
    fd, path = tempfile.mkstemp(prefix="scraper_out_", suffix=".txt")
    f = os.fdopen(fd, "wb")
    try:
        proc = subprocess.Popen(cmd, stdout=f, stderr=f)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            f.close()
            try:
                os.remove(path)
            except Exception:
                pass
            return -1, "", True
        f.flush()
        f.close()
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as rf:
                out = rf.read()
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
        return proc.returncode, out, False
    finally:
        # ensure file descriptor closed if something went wrong
        try:
            f.close()
        except Exception:
            pass


def run_with_pipe(cmd: list[str], timeout: float) -> Tuple[int, str, bool]:
    try:
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, text=True)
        return completed.returncode, completed.stdout or "", False
    except subprocess.TimeoutExpired:
        return -1, "", True


def main() -> int:
    parser = argparse.ArgumentParser(description="Test remote execution of bbcgoodfood_scraper_yolo.py")
    parser.add_argument("query", nargs="+", help="Search query to pass to scraper")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-attempt timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="Number of retries on timeout")
    parser.add_argument("--mode", choices=("pipe", "tempfile"), default="tempfile", help="How to capture subprocess output")
    args = parser.parse_args()

    script = os.path.join(os.path.dirname(__file__), "bbcgoodfood_scraper_yolo.py")
    if not os.path.exists(script):
        script = "bbcgoodfood_scraper_yolo.py"

    cmd = [sys.executable, script, " ".join(args.query)]

    attempt = 0
    start = time.time()
    while attempt <= args.retries:
        attempt += 1
        attempt_start = time.time()
        if args.mode == "tempfile":
            code, out, timed_out = run_with_tempfile(cmd, args.timeout)
        else:
            code, out, timed_out = run_with_pipe(cmd, args.timeout)

        elapsed = time.time() - attempt_start
        result = {
            "attempt": attempt,
            "returncode": code,
            "timed_out": bool(timed_out),
            "elapsed_seconds": round(elapsed, 2),
            "output": out,
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if not timed_out:
            # success or script error (non-zero return), stop retrying
            break

        if attempt > args.retries:
            break

        # exponential backoff
        backoff = 2 ** (attempt - 1)
        time.sleep(backoff)

    total = time.time() - start
    print(f"Total elapsed: {total:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
