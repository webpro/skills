#!/usr/bin/env python3

import os
import signal
import subprocess
import sys


def stop_group(process: subprocess.Popen[bytes], sig: signal.Signals) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run-with-deadline.py <seconds> <command> [args...]", file=sys.stderr)
        return 64

    seconds = int(sys.argv[1])
    try:
        process = subprocess.Popen(sys.argv[2:], stdin=subprocess.DEVNULL, start_new_session=True)
    except FileNotFoundError:
        print(f"error: command not found: {sys.argv[2]}", file=sys.stderr)
        return 127

    def forward_signal(sig: int, _frame: object) -> None:
        stop_group(process, signal.Signals(sig))
        raise SystemExit(128 + sig)

    signal.signal(signal.SIGTERM, forward_signal)
    signal.signal(signal.SIGHUP, forward_signal)

    try:
        status = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        stop_group(process, signal.SIGTERM)
        return 124
    except KeyboardInterrupt:
        stop_group(process, signal.SIGINT)
        return 130

    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    raise SystemExit(main())
