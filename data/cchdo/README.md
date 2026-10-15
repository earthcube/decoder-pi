# CCHDO graph (GeoCODES release)

`cchdo_release.nq.gz` is the GeoCODES graph release for CCHDO (the CLIVAR and
Carbon Hydrographic Data Office), gzip -9 compressed.

- Source: https://oss.geocodes-aws-dev.earthcube.org/geocodes/graphs/latest/cchdo_release.nq
- Downloaded: 2026-10-15
- Size: 4.4 MB gzipped, 110.4 MB uncompressed (over GitHub's 100 MB file limit, so only the .gz is kept)
- Contents: 551,904 N-Quads in 2,560 named graphs; 3,094 `schema:Dataset` records

## Use

sparqld ignores `.gz` files, so gunzip before serving:

```sh
gunzip -k data/cchdo/cchdo_release.nq.gz
mkdir -p /tmp/cchdo && mv data/cchdo/cchdo_release.nq /tmp/cchdo/
sparqld /tmp/cchdo
```

The Python fallback reads the `.gz` directly:
`uv run --with pyoxigraph python skills/sparqld/scripts/local_sparql.py data/cchdo/cchdo_release.nq.gz -q '...'`

## License and citation

- CCHDO data are public domain (CC0) by default. Some cruises were submitted
  under CC BY at the submitter's request; those are marked on the cruise page and
  their requested citation is in the data file header.
  See https://learning.cchdo.io/policies_and_procedures/data_license
- CCHDO asks that users cite the CCHDO archive snapshot (with its DOI) closest to
  the access date: https://learning.cchdo.io/policies_and_procedures/how_to_cite
- These triples are GeoCODES-derived metadata, not CCHDO data files. The license
  for the derived triples has not been confirmed with GeoCODES. In the triples,
  Datasets carry `schema:isAccessibleForFree true` and no `schema:license`.
