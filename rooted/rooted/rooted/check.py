"""Check that every employer's board slug works before adding it to the list.

Usage: python -m rooted.check data/employers.json
"""
import json
import sys
from pathlib import Path

from .sources import fetch_employer


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/employers.json"
    for emp in json.loads(Path(path).read_text()):
        try:
            n = len(fetch_employer(emp))
            status = "OK " if n else "EMPTY"
            print(f"{status:6} {emp['id']:28} {emp['ats']:10} {n} jobs")
        except Exception as exc:
            print(f"FAIL   {emp['id']:28} {emp['ats']:10} {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
