# SetGo Skill

Use this skill to guide domain scientists through the full metadata assessment-to-publication
workflow for scientific AI datasets. SetGo evaluates FAIR compliance, checks data governance
policy, generates portable data cards, and publishes Croissant/HuggingFace/CKAN/Observatory
catalog records from a `metadata.json` file.

SetGo does not require REDI. A `metadata.json` can come from three places:
- **REDI pipeline output** (the original workflow),
- **`setgo init <path>`** — introspect a raw file/directory and scaffold one from scratch, or
- **`setgo import <record>`** — pull an existing published record (e.g. a Hugging Face
  dataset) back into a `metadata.json` to re-assess, repair, or migrate it.

If there is no `metadata.json` yet, pick the entry point that matches the user's starting
material (raw data on disk → `init`; a published dataset → `import`) before the enrichment
loop below.

## When to Use

Invoke this skill when a user:
- Wants to know how FAIR-ready a dataset is
- Needs to identify and fill metadata gaps before publishing
- Wants to check governance policy compliance (license, provenance, FAIR threshold)
- Wants to generate a human-readable data card for a dataset
- Is ready to publish to a catalog (Croissant, Hugging Face Hub, CKAN, AMSC, Observatory)

## Commands

```bash
setgo init    <path> [-d domain] [--checksums] [--force]   # scaffold metadata.json from raw data
setgo import  <record> [-c huggingface] [-d domain] [-o dir]  # pull a published record into metadata.json
setgo fair    <output_dir> [-d domain] [--style json]   # FAIR assessment
setgo check   <output_dir> [-p policy] [--style json]   # governance compliance
setgo card    <output_dir> [--format setgo|modcon] [--no-prompt]  # generate data card
setgo publish <output_dir> [-c catalog] [--style json] # publish to catalog
```

`init` and `import` both write (or enrich, never clobbering human-entered values) a
`metadata.json` that the rest of the workflow consumes. `import` pulls the metadata record
only — card frontmatter, `dataset_info`, description — never the bulk data payload. After
either, proceed to the enrichment loop (assess → identify gaps → prompt → patch → re-assess).

Domains: `climate` `materials` `life_sciences` `fusion` `hpc` `general`
Policies: `minimal` `standard` `strict`
Catalogs: `croissant` `huggingface` `ckan` `observatory` `amsc` `openmetadata` `mlflow` `intake`

## Enrichment Loop

This is the primary use case: start from a raw REDI `metadata.json`, identify gaps,
collect the missing information from the scientist, patch the file, and publish.

### Step 0 — Pre-populate from sidecar files

**Do not read any files yet.** Ask the user this question first and wait for
their answer before touching the filesystem:

> "I can scan the dataset directory for existing sidecar files (DATA_CARD.md,
> PROVENANCE_CARD.md, flowcept_buffer.jsonl) and pre-populate metadata fields
> automatically from what I find. Would you like me to do that, or would you
> prefer to be prompted for each field yourself?"

If the user declines, skip the rest of Step 0 entirely and proceed to Step 1.
All fields will be collected interactively in Step 3 as normal.

Only if the user agrees: scan the dataset directory for sidecar files and
extract what you can. Do not read any files before receiving a yes.

**From `metadata.json` itself** (always present):
- `provenance.source` ← `input_file` field
- `domain` ← already set; map `xgc1` → `fusion` for FAIR/governance purposes
- Infer a draft `title` from the case name key inside `xgc1_cases` (e.g.
  `n560fr_ITER_PFPO_W_Ne` → "XGC1 ITER Pre-Fusion Power Operation Simulation (W+Ne)")
- Infer a draft `description` from mesh and timestep stats (num_nodes, num_planes,
  num_wedges, count of timesteps, impurity species from the case name)
- Infer draft `keywords` from domain + case name tokens (e.g. `fusion`, `plasma`,
  `XGC1`, `ITER`, `gyrokinetic`, `PFPO`)

**From `PROVENANCE_CARD.md`** (if present):
- `provenance.pipeline` ← tool name and version from the footer
  (e.g. "REDI full_pipeline (FlowCept 0.10.1)")
- `provenance.workflow_id` ← Workflow ID field
- `provenance.campaign_id` ← Campaign ID field

**From `DATA_CARD.md`** (if present):
- `contains_pii` ← "Contains PII" field

**From `flowcept_buffer.jsonl`** (if present):
- Any additional workflow or campaign IDs not already captured above

Once extraction is complete, show the user everything you found. Present it as
a summary, for example:

> Here's what I found in the directory:
>
> - **title** (inferred from case name): "XGC1 ITER Pre-Fusion Power Operation Simulation (W+Ne)"
> - **description** (inferred from mesh/timestep stats): "XGC1 gyrokinetic simulation..."
> - **keywords** (inferred): fusion, plasma, XGC1, ITER, gyrokinetic, PFPO
> - **provenance.source**: /lustre/orion/world-shared/prj001/...
> - **provenance.pipeline**: REDI full_pipeline (FlowCept 0.10.1)
> - **provenance.workflow_id**: d7c027e1-...
> - **contains_pii**: false
>
> Two fields can't be inferred from the sidecar files — I'll ask for those next.
> Let me know if you'd like to change any of the above first.

After the user confirms or corrects the pre-populated fields, ask for `license`
and `creators` (see Step 3 for prompts). Collect all corrections plus `license`
and `creators` before touching the filesystem. Only then write everything to
`metadata.json` in one operation. Do not write until both `license` and
`creators` are in hand.

### Step 1 — Assess

Before running the assessment, read `metadata.json` and extract the `domain` field.
Map it to the `-d` flag as follows:

| `domain` value in metadata.json | `-d` flag |
|---------------------------------|-----------|
| `climate`                       | `climate` |
| `materials`                     | `materials` |
| `fusion` or `xgc1`              | `fusion` |
| `life_sciences`                 | `life_sciences` |
| `hpc`                           | `hpc` |
| absent or unrecognised          | *(omit `-d`)* |

Then run the assessment with the domain flag if one was found:

```bash
setgo fair ./my_dataset -d <domain> --style json
```

Domain-specific validators run automatically when `-d` is supplied (e.g. CF Conventions
and ACDD 1.3 for `climate`, OPTIMADE for `materials`). Their findings appear alongside
the standard FAIR principles in the output and should be treated the same way — any
`NOT_COMPLIANT` or `PARTIALLY_COMPLIANT` result drives a prompt in step 3.

The JSON output has the structure below. Parse `principles` for entries where
`score == "NOT_COMPLIANT"` or `score == "PARTIALLY_COMPLIANT"`; the `recommendations`
list tells you exactly what to ask the scientist.

```json
{
  "overall_score": 0.57,
  "category_scores": { "findable": 0.42, "accessible": 0.78, "interoperable": 0.56, "reusable": 0.58 },
  "principles": {
    "F1": {
      "score": "NOT_COMPLIANT",
      "evidence": ["No persistent identifier found"],
      "recommendations": ["Assign a globally unique persistent identifier (DOI recommended)"]
    },
    "R1.1": {
      "score": "NOT_COMPLIANT",
      "evidence": ["No license specified"],
      "recommendations": ["Specify an open license (CC-BY-4.0 recommended for scientific data)"]
    }
  }
}
```

### Step 2 — Identify gaps

From the non-compliant principles, collect the fields to prompt for:

| Principle | Field in metadata.json |
|-----------|----------------------|
| F1 / F3   | `doi` or `persistent_identifier` |
| F2        | `title`, `description`, `keywords` |
| R1.1      | `license` (SPDX ID, e.g. `CC-BY-4.0`) |
| R1.2      | `provenance` (object with `source`, `pipeline`, `version`) |
| R1.3      | `community_standard` (e.g. `CF Conventions 1.10`) |
| I1        | `vocabulary_standard` |

### Step 3 — Prompt the scientist

Ask for the missing fields one at a time. Suggested prompts:

- **title** — "What is the human-readable name for this dataset?"
- **description** — "Describe what this dataset contains and how it was produced (1–3 sentences)."
- **license** — "Under what license should this dataset be released? (CC-BY-4.0 is standard for ORNL open data)"
- **doi** — "Has a DOI been minted for this dataset? If not, one can be assigned at publication time."
- **creators** — "List the people or organizations that should be credited as dataset creators in the catalog (First Last, or Org Name). These appear in Croissant and CKAN records."
  After the user provides each name, look up ORCID candidates from the decoder-pi repo root. Do not `import setgo` in the harness Python. `setgo` on `PATH` does not make that import work. This command loads the SetGo checkout for this call only:

  ```bash
  uv run --no-project --with-editable /home/fils/src/git/setgo \
    python skills/setgo/scripts/lookup_orcid.py "First Last"
  # optional: --institution "Oak Ridge National Laboratory"
  ```

  It prints a JSON list of `{orcid, name, institution}`. An empty list means nothing was found or the ORCID API was unreachable.
  If one or more candidates are returned, show them to the user:
  > "I found the following ORCID record(s) for 'Josiah Carberry':
  >   1. Josiah Carberry — Brown University (https://orcid.org/0000-0002-1825-0097)
  >   Is this the right person, or would you like to enter an ORCID manually (or skip)?"
  Store the confirmed ORCID alongside the name as `{"name": "...", "orcid": "https://orcid.org/..."}`.
  If no candidates are found, store the name as a plain string and move on — ORCID is optional.
- **authors** — "List the authors for the data card and HuggingFace Hub (First Last). These may overlap with creators but are stored separately."
- **keywords** — "Provide 3–5 subject keywords separated by commas."
- **provenance.source** — "What is the original source dataset or instrument?"

> **`creators` vs `authors`**: These are distinct fields. `creators` is required by the
> CKAN Croissant plugin (ckanext-dcat) and populates the `sc:creator` field in the
> Croissant JSON-LD. `authors` is used by `setgo card` (data cards) and HuggingFace
> export. Collect both when publishing to CKAN or Observatory.

> **Enrichment vs. publishing credentials**: All prompts in steps 3–4 are about
> *metadata quality* — they are driven by FAIR gaps and affect the dataset record.
> Publishing credentials (catalog token, repository/org slug) are *not* collected here.
> They are solicited separately, immediately before `setgo publish` is run, only when the
> user indicates they are ready to publish. Never ask for a token or repo during
> enrichment.

### Step 4 — Patch metadata.json

Collect **all** fields identified as gaps in Step 3 before writing. Write
`metadata.json` once with everything at the same time — do not write after each
individual answer. The key enrichment fields are:

```json
{
  "title": "...",
  "description": "...",
  "license": "CC-BY-4.0",
  "doi": "10.5281/zenodo.XXXXXXX",
  "creators": [
    { "name": "First Last", "orcid": "https://orcid.org/0000-0000-0000-0000" }
  ],
  "authors": ["First Last", "Second Person"],
  "keywords": ["climate", "ERA5", "AI-ready"],
  "domain": "climate",
  "provenance": {
    "source": "ERA5 reanalysis (ECMWF)",
    "pipeline": "REDI v1.0",
    "version": "1.0.0"
  }
}
```

`creators` is a list of objects with `name` (required) and optional `orcid`. It drives
the `sc:creator` field in Croissant JSON-LD and the `creator` field in CKAN/Observatory
packages. `authors` is a flat list of name strings used by data cards and HuggingFace.
`domain` is passed through to CKAN/Observatory as a tag and as `setgo_domain` in the
package extras.

### Step 5 — Re-assess and check governance

```bash
setgo fair ./my_dataset -d <domain> --style json   # same domain flag as step 1
setgo check ./my_dataset --policy strict --style json
```

The `setgo check` JSON output uses this shape:

```json
{
  "status": "compliant",
  "compliance_score": 1.0,
  "violations": [],
  "checks": [
    { "name": "license_required", "passed": true },
    { "name": "provenance_required", "passed": true },
    { "name": "fair_compliance", "passed": true, "message": "FAIR score 0.91 >= 0.7" }
  ]
}
```

Target: `status == "compliant"` and overall FAIR score ≥ 0.70 before publishing.

**If the score remains below 0.70**, do not silently block or proceed. Instead:

1. Identify which principles are still `NOT_COMPLIANT` or `PARTIALLY_COMPLIANT` and
   map them to the specific fields listed in Step 2.
2. Tell the scientist exactly which fields are holding the score down and what filling
   them would contribute. Example:
   > "The FAIR score is currently 0.58. The two gaps keeping it below 0.70 are a missing
   > DOI (F1 — worth ~0.10) and no provenance source (R1.2 — worth ~0.08). Would you
   > like to provide these now, or publish anyway with a warning?"
3. If the user cannot or does not want to fill the remaining gaps, offer to proceed with
   an explicit acknowledgement that the dataset does not yet meet the 0.70 threshold.
   Do not block publication — the threshold is a quality gate, not a hard lock.

**If the score reaches ≥ 0.70 and governance is compliant**, proactively offer to move
forward. Do not wait for the user to ask. Say something like:
> "The FAIR score is now 0.82 and the dataset passes governance checks. Would you like
> to generate a data card, publish to a catalog, or both?"

This is the natural handoff point from enrichment to publication. If the user says yes
to publishing, proceed to the credential prompts in Step 7 — do not return to metadata
questions unless the user asks.

### Step 6 — Generate data card (optional)

Two formats are available. Ask the scientist which they need before running:

**Default (SetGo format)** — a concise Markdown card suitable for Hugging Face Hub,
Croissant sidecars, and general sharing:

```bash
setgo card ./my_dataset --no-prompt
# writes: DATA_CARD.md
```

**ModCon v1 format** — a structured YAML-frontmatter + Markdown card that follows
the ModCon/ORNL datacard schema. Use this when the dataset is heading to an ORNL
repository, a DOE data portal, or any system that consumes ModCon datacards:

```bash
setgo card ./my_dataset --format modcon --no-prompt
# writes: modcon_datacard_<snake_case_title>.md
```

Both formats require the same four fields to be present in `metadata.json` (or passed
as CLI flags): `title`, `description`, `authors`, `license`. Note: data cards use
`authors` (flat name strings), not `creators`.

**What ModCon auto-populates from `metadata.json`:**
- YAML frontmatter: `title`, `license.spdx_id`, `dataset_authors`, `dataset_info`
  (format, features), `categorization.science_domain`, `dataset_provenance`
  (source, pipeline, processing steps), `dates` (collection start/end, issued),
  `semantic_layer.controlled_vocabularies`, `ai_usage` flags, `dataset_counts`,
  `access_policy` (defaults: open, unclassified, no auth), `security_marking`
- Markdown body: description, keywords, provenance narrative, methods, features table,
  CF/domain standard references

**What stays as `[!TODO]` and needs human completion after generation:**
- `project`, `contact_point`, `originating_research_organization` (ROR ID)
- `facilities`, `fundings` (award numbers, funder ROR)
- `dataset_readiness.level` (1 / 2 / 3 per Genesis model)
- `review_process`, `distribution_statement`
- `data_quality`, `integrity` (checksums), `dataset_storage` (byte sizes)

If the scientist knows any of these before card generation, collect them and add to
`metadata.json` first — the generator will pick them up automatically for the fields
it knows how to map, and the rest can be filled in the generated file directly.

### Step 7 — Publish

```bash
# Croissant 1.0 JSON-LD sidecar (local, no auth required)
setgo publish ./my_dataset -c croissant

# Hugging Face Hub
setgo publish ./my_dataset -c huggingface --repo org/dataset-name --token $HF_TOKEN

# CKAN instance
setgo publish ./my_dataset -c ckan --host https://data.example.org --token $CKAN_TOKEN

# ORNL Observatory (CKAN-based, custom REST API at /olcf/open/v1/observatory/…)
setgo publish ./my_dataset -c observatory --token $OBSERVATORY_API_KEY --repo <owner-org>
```

`setgo publish` generates per-file SHA-256 checksums, infers license conditions from the
SPDX registry, and embeds W3C PROV-O provenance from the `provenance` block.

For Observatory, `--repo` sets the `owner_org` on the package (same behaviour as CKAN).
The token can also be supplied via the `OBSERVATORY_API_KEY` environment variable.
The `Bearer ` prefix is added automatically — pass the raw token value only.
The default host is `https://testing.s3m.olcf.ornl.gov`; override with `--host` only if
targeting a different instance.

**Observatory credential prompts (before running publish)**

Before invoking `setgo publish -c observatory`, confirm that `metadata.json` has already
been written (Step 4 complete). Do not ask for credentials while metadata fields are still
being collected — finish the enrichment write first, then prompt for credentials as a
separate step. Present the credential prompts the way a CLI tool asks for username and
password, not as part of metadata enrichment.

1. **S3M token** — Ask:
   > "Publishing to the ORNL S3M Observatory requires an OLCF token. Do you have an
   > S3M OPAT (personal access token)?"
   - If yes: ask them to paste it. Pass as `--token <value>` (Bearer prefix is added automatically).
   - If no: direct them to **https://my.olcf.ornl.gov/** to generate one, then wait for
     them to return with the token before proceeding.
   - **Always assign the token to a shell variable before passing it to the command.**
     Embedding a long JWT token inline in a shell command risks transcription errors that
     silently corrupt the value and produce a 401. Use this pattern instead:
     ```bash
     TOKEN="<pasted-value>"
     setgo publish . -c observatory --token "$TOKEN" --repo "<slug>"
     ```

2. **Repository (owner org)** — Ask:
   > "Which S3M project or organization should own this dataset? (This is the short slug
   > shown in the S3M project list, e.g. `stf249`.)"
   - Pass as `--repo <slug>`.

**CKAN / Observatory pre-flight gate** — both exporters hard-block before any network
call if any of these four fields are absent (after applying CLI overrides):

| Field | Must be set in `metadata.json` or passed via |
|-------|---------------------------------------------|
| `title` | `--title "..."` |
| `description` | *(metadata.json only)* |
| `creators` | `--creators "First Last,Second Person"` |
| `license` | `--license CC-BY-4.0` |

The error message lists every missing field at once. Keywords (`setgo`, `ai-ready`, and
`domain` if set) are auto-generated and never need to be supplied manually.

The `--creators` flag (comma-separated names) can satisfy the gate at publish time without
modifying `metadata.json`. Use it when the metadata file is read-only or the creator list
differs from what is stored in `authors`.

## Domain-Specific Validators

When `-d climate` is passed to `setgo fair`, two additional validators run:
- **CF Conventions** — checks NetCDF files for `Conventions` attribute and `standard_name` on variables
- **ACDD 1.3** — checks for required/recommended global attributes (`title`, `summary`, `keywords`, etc.)

Similarly `-d materials` runs the OPTIMADE validator for structural metadata fields.

## Example: Climate Dataset (from raw REDI output to Croissant)

```bash
# 1. Assess — score is 57%, F1/R1.1/R1.2 are NOT_COMPLIANT
setgo fair ./climate/before -d climate --style json

# 2. (LLM agent collects title, description, license, doi, creators, provenance from scientist)
# 3. (Patch metadata.json with collected fields)

# 4. Re-assess — score should reach ~91%
setgo fair ./climate/after -d climate --style json

# 5. Governance check
setgo check ./climate/after --policy strict --style json

# 6. Publish
setgo publish ./climate/after -c croissant
```
