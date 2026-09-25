#!/usr/bin/env python3
"""Look up ORCID iDs by name. Prints a JSON list.

Run from the decoder-pi repo root so SetGo is imported from the checkout,
not from this harness environment:

    uv run --no-project --with-editable /home/fils/src/git/setgo \
      python skills/setgo/scripts/lookup_orcid.py "First Last"
"""

from __future__ import annotations

import argparse
import json

from setgo.orcid import lookup_orcid


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up ORCID iDs by name")
    parser.add_argument("name", help="Full name, e.g. 'Josiah Carberry'")
    parser.add_argument("--institution", help="Affiliation, if known")
    parser.add_argument("--email", help="Public email, if known")
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args()
    candidates = lookup_orcid(
        args.name,
        institution=args.institution,
        email=args.email,
        max_results=args.max_results,
    )
    print(json.dumps(candidates, indent=2))


if __name__ == "__main__":
    main()
