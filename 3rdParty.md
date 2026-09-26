# Third-party efforts

This harness does not reimplement these projects. `./bin/pi` starts Pi in the
repo root, so `.mcp.json` is discovered as project MCP config, and
`extensions/load-skills.ts` contributes `skills/`. AIDRIN and OKN arrive as
MCP servers. SetGo arrives as a skill that calls the SetGo command.

## AIDRIN

[AIDRIN](https://www.aidrin.org/) (AI Data Readiness Infrastructure) scores
whether a tabular file is ready for AI work: quality, structure, fairness, and
privacy. It reads CSV, Excel, JSON, Parquet, NumPy, and HDF5. The harness uses
the MCP server, not the web app.

| | |
|---|---|
| Web | https://www.aidrin.org/ |
| Docs | https://aidrin.readthedocs.io/en/latest/ |
| GitHub | https://github.com/idtlab/AIDRIN |
| Paper | https://arxiv.org/abs/2406.19256 |

AIDRIN is an optional uv group, `aidrin[mcp]` in `pyproject.toml`. A default
`uv sync` does not install it. After `uv sync --group aidrin`, the `aidrin`
entry in `.mcp.json` starts `uv run --group aidrin aidrin-mcp` as a stdio
server for the session. Catalog skills find a file (for example one ecoforecast
parquet or a deepoceans CSV). AIDRIN scores that file. A worked session is in
[`AIDRIN_EXAMPLE.md`](AIDRIN_EXAMPLE.md).

Tools exposed by the `aidrin` server on 2026-09-26:

| Tool | What it does |
|---|---|
| `aidrin_summarize_dataset` | Summarize a dataset's numerical and categorical fields |
| `aidrin_list_metrics` | List all available AIDRIN metrics by group |
| `aidrin_run_data_quality_check` | Run the three core data-quality metrics |
| `aidrin_run_aidrin_metric` | Run a single built-in AIDRIN metric |
| `aidrin_verify_file_references` | Validate file references in selected fields |
| `aidrin_run_custom_outlier_check` | Run custom-criteria outlier checks |
| `aidrin_run_batch` | Run multiple metrics declared in a YAML batch |
| `aidrin_list_remote_profiles` | List configured Globus Compute endpoint profiles |
| `aidrin_run_custom_metric` | Run the `metric()` method of a CustomDR class |
| `aidrin_run_custom_remedy` | Run the `remedy()` method of a CustomDR class |
| `aidrin_create_custom_metric` | Generate a CustomDR template `.py` file |
| `aidrin_agentic_build_index` | Build the FAISS vector index |
| `aidrin_agentic_run` | Run the full AIDRIN agentic evaluation |
| `aidrin_start_assessment` | Open an MLflow-tracked assessment |
| `aidrin_end_assessment` | Close a tracked assessment |

## SetGo

[SetGo](https://code.ornl.gov/drai/setgo) assesses and repairs the metadata
record of a scientific dataset before publication. It scores FAIR compliance,
licensing, provenance, governance, reproducibility, and catalog readiness from
`metadata.json`, then can publish a Croissant sidecar or push to Hugging Face,
CKAN, or similar catalogs. It does not score the data bytes. That is AIDRIN's
job.

| | |
|---|---|
| Source | https://code.ornl.gov/drai/setgo |
| DOI | https://doi.org/10.11578/dc.20260708.9 |
| Paper | https://arxiv.org/abs/2607.22677 |

SetGo is not on GitHub and is not published to PyPI. The source repository is
ORNL GitLab. This harness loads it as `skills/setgo/`, alongside the catalog
skills, not as an MCP server. The skill tells the agent to run the `setgo`
command already on `PATH` (`fair`, `check`, `card`, `publish`). ORCID name
search is a small script in that skill, run against a local checkout:

```bash
uv run --no-project --with-editable /home/fils/src/git/setgo \
  python skills/setgo/scripts/lookup_orcid.py "First Last"
```

## OKN

The [Open Knowledge Network](https://okn.us/) is a federation of scientific
knowledge graphs (biology, health, environment, climate, water, and others),
with a registry at [registry.okn.us](https://registry.okn.us/). The program
overview is [proto-okn.net](https://www.proto-okn.net/). Its MCP server lets an
assistant list those graphs, read their schemas, and query them with SPARQL.

| | |
|---|---|
| Web | https://okn.us/ |
| MCP docs | https://okn.us/mcp |
| Registry | https://registry.okn.us/ |
| GitHub | https://github.com/sbl-sdsc/mcp-proto-okn |

The harness does not clone that repository. The `okn` entry in `.mcp.json` is
a remote server, `https://apps.okn.us/okn-mcp-dev/mcp`, with lazy startup and
authentication off. That is the hosted endpoint documented on
[okn.us/mcp](https://okn.us/mcp). The same `./bin/pi` launch that picks up
AIDRIN picks up this server.

Tools exposed by that server on 2026-09-26:

| Tool | What it does |
|---|---|
| `okn_get_valid_contrasts` | Vetted spaceflight differential-expression contrasts |
| `okn_get_server_info` | Service, version, and build identity |
| `okn_list_kgs` | Proto-OKN knowledge graphs on the federation |
| `okn_describe_kg` | Registry documentation for one KG |
| `okn_get_kg_version` | Release version and last-updated time |
| `okn_get_join_strategy` | A precomputed, verified cross-KG join recipe |
| `okn_taxon_overlap` | A runnable NCBITaxon overlap query |
| `okn_list_crosswalks` | Every precomputed cross-KG integration point |
| `okn_find_context_sources` | Which KGs supply a given context |
| `okn_sparql_to_mermaid` | Render a SPARQL query as a Mermaid flowchart |
| `okn_probe_namespaces` | Identifier and ontology namespaces in a KG |
| `okn_find_crosswalks` | Find ontology or database ids in a KG |
| `okn_sparql_query` | Run SPARQL against the OKN federation |
| `okn_expand_ontology_term` | Expand an ontology term |
| `okn_point_to_s2` | Convert a lat/long point to a spatialkg S2 cell |
| `okn_spatial_bridge` | Generic point-to-S2 bridge for any point-bearing KG |
| `okn_get_schema` | Classes, predicates, and edge/node schema |
| `okn_visualize_schema` | Mermaid class diagram of a KG schema |
| `okn_reset_query_log` | Clear this analysis's query log |
| `okn_get_query_log` | SPARQL queries logged so far |
| `okn_get_skipped_queries` | Queries that ran but were kept out of the log |
| `okn_create_chat_transcript` | Reproducible transcript of a chat |
| `okn_create_reproducibility_record` | Header plus reproducibility record |
| `okn_read_latest_chat_transcript` | Most recent rendered transcript |
