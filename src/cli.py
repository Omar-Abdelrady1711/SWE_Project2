from __future__ import annotations
import argparse
import sys
from utils.parse import read_urls_from_file, infer_category_from_url
from scorer import score_urls
from utils.output import write_ndjson


def main(argv=None):
	p = argparse.ArgumentParser(prog="acme-scorer")
	p.add_argument("urls", nargs="*", help="URLs to score (or pass --input-file)")
	p.add_argument("--input-file", help="File containing one URL per line")
	p.add_argument("--format", choices=("ndjson", "json"), default="ndjson")
	args = p.parse_args(argv)

	urls = list(args.urls or [])
	if args.input_file:
		urls.extend(list(read_urls_from_file(args.input_file)))

	if not urls:
		p.print_help()
		return 2

	results = score_urls(urls)
	if args.format == "ndjson":
		write_ndjson(results, sys.stdout)
	else:
		# minimal JSON array output
		import json
		from dataclasses import asdict
		print(json.dumps([asdict(r) for r in results], ensure_ascii=False))

if __name__ == "__main__":
	raise SystemExit(main())
