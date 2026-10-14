---
name: handoff
description: >
  Update a local human-gated handoff record so the next session reads the
  committed file. Use when a decision, a failed approach, the current state,
  the next action, or a blocker should outlive the chat. Triggers: handoff,
  session continuity, rejected approach, next-session authority, /skill:handoff.
license: Apache-2.0
compatibility: python3, uv (decoder-pi pyproject.toml). Optional stdio MCP when the mcp package imports.
metadata:
  project: decoder-pi
  version: "1.0"
---

# Handoff

The next session reads `skills/handoff/handoff/HANDOFF.md`. That file is the authority. `HANDOFF_toBuildHandoff.md` is the build spec for this example. The field list is `HANDOFF_TEMPLATE.md`.

`status` is `done`, `partial`, or `blocked`.

- `done`: do not continue the task.
- `blocked`: do not guess. Stop and ask.
- `partial`: do the `next` field and nothing else.

## Before acting

Read the committed file. This command does not return the draft.

```bash
uv run python skills/handoff/scripts/handoff_mcp.py read
```

Run it from the decoder-pi repo root.

## When a field changes

When the conversation establishes a decision, a failed approach, a new current state, a next action, or a blocker, propose that field only. If none of those changed, write nothing. Do not write a chronicle of the chat.

Allowed fields are the ones in `HANDOFF_TEMPLATE.md`. List fields (`decisions`, `rejected`, `artifacts`) append one item. The other fields replace the proposed value. `evidence` stays in the draft.

```bash
uv run python skills/handoff/scripts/handoff_mcp.py propose \
  --field rejected \
  --value "retry login with the same expired token" \
  --evidence "the token was already expired"
```

After proposing, stop and wait. A human commits or rejects on a TTY. `commit` defaults to reject. There is no approve flag.

```bash
uv run python skills/handoff/scripts/handoff_mcp.py commit
uv run python skills/handoff/scripts/handoff_mcp.py reject
```

Writes go through this script. Do not edit `HANDOFF.md` or `HANDOFF.draft.md` with the file editor.

## Check

```bash
uv run python skills/handoff/demo.py
```

The script prints `PASS` or `FAIL`. It does not call a model.
