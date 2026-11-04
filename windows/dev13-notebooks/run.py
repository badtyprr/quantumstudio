"""Execute finite reviewed notebook contracts with explicit offline environments."""
import argparse
import json
from pathlib import Path
import sys

from execution import cancel, create_environment, execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("environment")
    setup.add_argument("--profile", required=True)
    setup.add_argument("--python", type=Path, required=True)
    setup.add_argument("--wheelhouse", type=Path, required=True)
    setup.add_argument("--destination", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--contract", required=True)
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--environment", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    stop = commands.add_parser("cancel")
    stop.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "environment":
            result = create_environment(args.profile, args.python, args.wheelhouse, args.destination)
        elif args.command == "cancel":
            result = cancel(args.run)
            print(json.dumps({"state": result["state"], "request_recorded": result["state"] not in {"succeeded", "failed", "cancelled"}}))
            return 0
        else:
            result = execute(vars(args))
        print(json.dumps({"state": result["state"], "error": result.get("error"), "cleanup": result.get("cleanup")}))
        return {"succeeded": 0, "cancelled": 2}.get(result["state"], 1)
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
