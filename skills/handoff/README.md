# Handoff gate

Local example of a human-gated handoff record. The next session reads `handoff/HANDOFF.md`. The model may draft into `handoff/HANDOFF.draft.md`. A draft becomes authority only after a human approves it.

The blank field list is `HANDOFF_TEMPLATE.md`. The procedure for an agent is `SKILL.md`.

From the decoder-pi repo root:

```bash
uv run python skills/handoff/demo.py
```

`demo.py` seeds the record, exercises propose / commit / reject, and prints `PASS` or `FAIL`. It does not call a model or the network. The default for commit is reject.

Commands take an optional `--root PATH` before or after the subcommand:

```bash
uv run python skills/handoff/scripts/handoff_mcp.py read
uv run python skills/handoff/scripts/handoff_mcp.py propose --field next --value "..." --evidence "..."
uv run python skills/handoff/scripts/handoff_mcp.py commit
uv run python skills/handoff/scripts/handoff_mcp.py reject
```

`commit` prompts on a TTY (`approve` or `reject`). Any other answer, and any run without a TTY, leaves the committed file unchanged.

`serve` starts a stdio MCP server when `mcp.server.mcpserver.MCPServer` imports (MCP Python SDK 2.x). A default `uv sync` does not install that package. This checkout's aidrin group does. If the import fails, `serve` exits and the plain functions in `scripts/handoff_mcp.py` remain the tool contract. The server's `handoff_commit` tool does not approve.

```bash
uv run python skills/handoff/scripts/handoff_mcp.py serve
```

An approval line in `handoff/audit.log` records the time, the fields changed, and `approved_by=human`.
