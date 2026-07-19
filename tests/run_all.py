"""Run every non-graphical automated suite with one command.

Run from the repository root:  python -B tests/run_all.py
"""

import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))
SUITES = ("test_static.py", "test_logic.py", "smoke_launch.py")


def run():
    for suite in SUITES:
        path = os.path.join(HERE, suite)
        print("\n=== {} ===".format(suite), flush=True)
        completed = subprocess.run(
            [sys.executable, "-B", path],
            cwd=PROJECT,
            check=False,
        )
        if completed.returncode != 0:
            print("FAILED: {} exited {}".format(suite, completed.returncode))
            return completed.returncode
    print("\nAll non-graphical automated suites passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
