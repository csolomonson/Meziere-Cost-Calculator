import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.queries import run_query


def read_sql(args):
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.sql:
        return args.sql
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide SQL with --sql, --file, or stdin.")


def main():
    parser = argparse.ArgumentParser(description="Run a read-only ERP query through the app connection.")
    parser.add_argument("--sql", help="SQL text to run.")
    parser.add_argument("--file", help="Path to a .sql file to run.")
    parser.add_argument("--param", action="append", default=[], help="Query parameter value. Repeat for :param1, :param2, etc.")
    parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
    parser.add_argument("--max-rows", type=int, default=100)
    args = parser.parse_args()

    sql = read_sql(args).strip()
    if not sql:
        raise SystemExit("SQL was empty.")

    rows = run_query(sql, tuple(args.param))
    if args.max_rows > 0:
        rows = rows.head(args.max_rows)

    clean_rows = rows.where(rows.notna(), None)
    if args.format == "json":
        print(json.dumps(clean_rows.to_dict(orient="records"), default=str, indent=2))
    elif args.format == "csv":
        print(clean_rows.to_csv(index=False))
    else:
        print(clean_rows.to_string(index=False))


if __name__ == "__main__":
    main()
