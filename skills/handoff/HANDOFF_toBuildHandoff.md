# Handoff

status: partial
goal: Build a small, runnable example of a human-gated handoff record — a SKILL that tells the agent when to update which field, and an MCP server that is the only write path. The next session reads the committed file, not the chat.
now: Design is settled in conversation. No code exists yet. This file is the spec and the session handoff.
decisions:
  - Persist the human correction in a structured file. Do not pass the transcript.
  - Enforcement lives in the write path, not in the prompt. A SKILL carries the procedure. An MCP tool is the boundary.
  - The model may draft freely. A human must approve before a draft becomes the file the next session treats as authority.
  - Scope is a code example, not the research-data stack (no Croissant, CDIF, DID, ODRL, vault, or Nectar).
rejected:
  - Prompt-only control. The model can ignore it or write around it if it has a normal file tool.
  - A running event log of "related conversation events." That recreates the transcript. Update a field, or write nothing.
  - DSPy as the session controller. DSPy is a later eval layer, not the gate.
  - SOUL.md or identity files as the learning record. Wrong object.
  - Treating this example as a measurement of whether AI is improving. The test is only: a fresh reader, given the committed file, does not repeat a rejected approach.
artifacts:
  - This document. It is the input to Grok Build.
next: Implement the example described under Build spec. Stop when the demo script passes.
blocked: none

## Why this shape

The interaction claim worth implementing is small. A person can stop, mark a path wrong, and the next agent sees that mark instead of the chat. Heavier packaging (signed dataset annotations, policy languages, cross-model vaults) is out of scope. A well-structured handoff file is current coding-agent practice, not a formal standard. AGENTS.md is for standing instructions. This file is the session artifact those instructions would point at.

## Build spec

Create a minimal Python example, local only, no accounts and no network.

Suggested layout:

```
handoff-gate/
  README.md
  handoff/
    HANDOFF.md          # committed authority; next session reads this
    HANDOFF.draft.md    # model proposals; not authority
  skill/
    SKILL.md            # procedure the agent is supposed to follow
  server/
    handoff_mcp.py      # MCP server; the only write path
  demo.py               # scripted proof, no LLM required
```

Use the official MCP Python SDK if it imports cleanly. If it does not, implement the same tool contract as plain functions and note that in the README. Do not block the example on protocol boilerplate.

### Committed file schema

`handoff/HANDOFF.md` is authority. Exact fields:

```markdown
# Handoff
status: partial
goal: <one sentence>
now: <where the work actually is>
decisions:
  - <choice made, and why>
rejected:
  - <approach tried, and why it failed>
artifacts:
  - <path or command that reproduces current state>
next: <single concrete action>
blocked: <what a human must decide, or none>
```

`status` is one of `done`, `partial`, `blocked`.

- `done`: the next session must not continue this task.
- `blocked`: the next session must not guess. Stop and ask.
- `partial`: do `next` and nothing else.

Keep the committed file small. No transcript. No narrative event dump.

### Tool contract

The model must not be given a raw file-edit tool for these two paths. Writes happen only through these tools.

`handoff_read`
Returns the committed file only. Never the draft.

`handoff_propose(field, value, evidence)`
Appends or replaces a proposal in `HANDOFF.draft.md`. Does not touch the committed file.
Allowed fields: `status`, `goal`, `now`, `decisions`, `rejected`, `artifacts`, `next`, `blocked`.
Reject any other field. Reject empty `value`. `evidence` is a short quote or reason, stored only in the draft, not copied into the committed file.
List fields (`decisions`, `rejected`, `artifacts`) append one item. Scalar fields replace the proposed value.
If `field` is `blocked` and `value` is not `none`, set proposed status to `blocked`.

`handoff_commit`
No effect unless a human has approved the current draft.
On approval, apply the draft onto `HANDOFF.md` and clear the draft.
Record an approval line in a local `handoff/audit.log`: timestamp, fields changed, and `approved_by: human`. This is the receipt. Not a signature scheme.

`handoff_reject_draft`
Discards the draft. Committed file unchanged. Log the rejection.

Approval mechanism for the example: a CLI flag or a prompt in `demo.py` (`approve` / `reject`). Do not auto-approve. Default is reject.

### SKILL behavior

`skill/SKILL.md` must tell an agent:

- Read `handoff_read` before acting.
- When the conversation establishes a decision, a failed approach, a new current state, a next action, or a blocker, call `handoff_propose` for that field only.
- If nothing in those fields changed, write nothing.
- Do not write a chronicle of the chat.
- After proposing, stop and wait for `handoff_commit` or `handoff_reject_draft`.
- If committed `status` is `blocked`, do not proceed.
- If committed `status` is `done`, do not continue the task.
- If committed `status` is `partial`, the only next action is the `next` field.
- Never edit `HANDOFF.md` directly.

### Demo script

`demo.py` must run without an LLM and print pass or fail.

1. Seed a committed handoff with one rejected approach, for example `retry login with the same expired token`.
2. Propose a new decision and a new rejected path. Show that `handoff_read` still returns the old committed file.
3. Call `handoff_commit` without approval. Show it does not change the committed file.
4. Approve, commit, and show `handoff_read` now contains the new fields and not the evidence notes.
5. Show `audit.log` has one approval line.
6. Propose `blocked: need a human to pick the auth scheme`, and show proposed status becomes `blocked`.
7. Reject that draft. Show the committed file is unchanged.

That is the example. Stop when this script passes.

## Out of scope

- Croissant, CDIF, DIDs, ODRL, MCP-as-a-standards-tour, digital vault, signposting, Nectar, Dataverse.
- Measuring whether a model is improving.
- Forcing a critical question. The gate checks that a human approved the record, not that they understood it.
- A vector database, a wiki, or OKF packaging. A later serialization can wrap this file. Do not start there.
- DSPy optimization. Optional follow-up, not this task.

## Optional follow-up, not this task

Once the gate exists, a separate eval can ask a fresh agent to continue from `handoff_read` only and score whether it repeats an item in `rejected`. That is the test the design is for. Do not build it in this pass.

## Note to the implementing agent

This document is itself a handoff. Treat it as committed authority for the example. Do not expand the scope. Implement the spec, run `demo.py`, and stop.
