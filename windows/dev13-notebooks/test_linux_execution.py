"""Hosted Linux prerequisite entry point; full lifecycle tests are not yet added."""
import argparse
from pathlib import Path
import sys

from linux_lifecycle import preflight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = preflight(args.output)
    print(report["state"])
    if report.get("error"):
        print(report["error"], file=sys.stderr)
    return 0 if report["state"] == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
