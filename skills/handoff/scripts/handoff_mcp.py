#!/usr/bin/env python3
"""Human-gated handoff record.

The committed file is the authority the next session reads. Proposals sit in
the draft until a human approves them. Evidence stays in the draft.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "handoff"
HEADER = "# Handoff"
DRAFT_HEADER = "# Handoff draft"

SCALAR_FIELDS = ("status", "goal", "now", "next", "blocked")
LIST_FIELDS = ("decisions", "rejected", "artifacts")
FIELD_ORDER = (
    "status",
    "goal",
    "now",
    "decisions",
    "rejected",
    "artifacts",
    "next",
    "blocked",
)
STATUSES = frozenset({"done", "partial", "blocked"})
BLOCKED_SENTINEL = "none"


class HandoffError(Exception):
    """The record could not be parsed or the call was refused."""


@dataclass
class Record:
    status: str
    goal: str
    now: str
    decisions: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    next: str = ""
    blocked: str = BLOCKED_SENTINEL

    def items(self, name: str) -> list[str]:
        value = getattr(self, name)
        if not isinstance(value, list):
            raise HandoffError(f"{name} is not a list field")
        return value

    def set_scalar(self, name: str, value: str) -> None:
        if name not in SCALAR_FIELDS:
            raise HandoffError(f"{name} is not a scalar field")
        setattr(self, name, value)


@dataclass
class Proposal:
    field: str
    op: str
    value: str
    evidence: str


def _root(root: Path | None) -> Path:
    return (root or DEFAULT_ROOT).resolve()


def _committed_path(root: Path) -> Path:
    return root / "HANDOFF.md"


def _draft_path(root: Path) -> Path:
    return root / "HANDOFF.draft.md"


def _audit_path(root: Path) -> Path:
    return root / "audit.log"


def _strip_comment(value: str) -> str:
    return re.sub(r"\s+#.*$", "", value)


def _as_list(value: str | list[str]) -> list[str]:
    if not isinstance(value, list):
        raise HandoffError("expected a list field")
    return list(value)


def parse_committed(text: str) -> Record:
    """Parse a committed handoff. Trailing ``#`` comments on scalar lines are ignored."""
    lines = text.splitlines()
    index = 0

    def skip_blank() -> None:
        nonlocal index
        while index < len(lines) and lines[index].strip() == "":
            index += 1

    skip_blank()
    if index >= len(lines) or lines[index].strip() != HEADER:
        raise HandoffError("committed file must start with '# Handoff'")
    index += 1

    found: dict[str, str | list[str]] = {}
    while True:
        skip_blank()
        if index >= len(lines):
            break
        line = lines[index]
        match = re.match(r"^([a-z]+):(.*)$", line)
        if match is None:
            raise HandoffError(f"bad line: {line}")
        key, rest = match.group(1), match.group(2)
        if key not in FIELD_ORDER:
            raise HandoffError(f"unknown field: {key}")
        if key in found:
            raise HandoffError(f"duplicate field: {key}")
        if key in LIST_FIELDS:
            index += 1
            items: list[str] = []
            while index < len(lines):
                item_line = lines[index]
                if item_line.strip() == "":
                    look = index
                    while look < len(lines) and lines[look].strip() == "":
                        look += 1
                    if look < len(lines) and lines[look].startswith("  - "):
                        index = look
                        continue
                    break
                if item_line.startswith("  - "):
                    items.append(item_line[4:])
                    index += 1
                    continue
                break
            found[key] = items
            continue
        found[key] = _strip_comment(rest).strip()
        index += 1

    missing = [name for name in FIELD_ORDER if name not in found]
    if missing:
        raise HandoffError("missing fields: " + ", ".join(missing))
    status = str(found["status"])
    if status not in STATUSES:
        raise HandoffError("status must be done, partial, or blocked")
    return Record(
        status=status,
        goal=str(found["goal"]),
        now=str(found["now"]),
        decisions=_as_list(found["decisions"]),
        rejected=_as_list(found["rejected"]),
        artifacts=_as_list(found["artifacts"]),
        next=str(found["next"]),
        blocked=str(found["blocked"]),
    )


def render_committed(record: Record) -> str:
    lines = [
        HEADER,
        f"status: {record.status}",
        f"goal: {record.goal}",
        f"now: {record.now}",
    ]
    for name in LIST_FIELDS:
        lines.append(f"{name}:")
        for item in record.items(name):
            lines.append(f"  - {item}")
    lines.append(f"next: {record.next}")
    lines.append(f"blocked: {record.blocked}")
    return "\n".join(lines) + "\n"


def parse_draft(text: str) -> list[Proposal]:
    if text.strip() == "":
        return []
    proposals: list[Proposal] = []
    current: dict[str, str] | None = None

    def finish() -> None:
        nonlocal current
        if current is None:
            return
        for slot in ("field", "op", "value", "evidence"):
            if slot not in current:
                raise HandoffError(f"draft proposal missing {slot}")
        proposals.append(
            Proposal(
                field=current["field"],
                op=current["op"],
                value=current["value"],
                evidence=current["evidence"],
            )
        )
        current = None

    for line in text.splitlines():
        if line.strip() == "" or line.startswith("# "):
            continue
        if line.startswith("- field: "):
            finish()
            current = {"field": line[len("- field: ") :]}
            continue
        if current is None:
            raise HandoffError(f"bad draft line: {line}")
        matched = False
        for slot in ("op", "value", "evidence"):
            prefix = f"  {slot}: "
            if line.startswith(prefix):
                current[slot] = line[len(prefix) :]
                matched = True
                break
        if not matched:
            raise HandoffError(f"bad draft line: {line}")
    finish()
    return proposals


def render_draft(proposals: list[Proposal]) -> str:
    if not proposals:
        return ""
    lines = [DRAFT_HEADER]
    for proposal in proposals:
        lines.append(f"- field: {proposal.field}")
        lines.append(f"  op: {proposal.op}")
        lines.append(f"  value: {proposal.value}")
        lines.append(f"  evidence: {proposal.evidence}")
    return "\n".join(lines) + "\n"


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _load_record(root: Path) -> Record:
    path = _committed_path(root)
    if not path.is_file():
        raise HandoffError("no committed handoff")
    return parse_committed(path.read_text(encoding="utf-8"))


def _load_proposals(root: Path) -> list[Proposal]:
    return parse_draft(_read_text(_draft_path(root)))


def _write_proposals(root: Path, proposals: list[Proposal]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _draft_path(root).write_text(render_draft(proposals), encoding="utf-8")


def _ordered(names: set[str]) -> list[str]:
    return [name for name in FIELD_ORDER if name in names]


def _append_audit(root: Path, kind: str, names: set[str]) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp} {kind} fields={','.join(_ordered(names))}"
    if kind == "commit":
        line += " approved_by=human"
    root.mkdir(parents=True, exist_ok=True)
    with _audit_path(root).open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _upsert(proposals: list[Proposal], proposal: Proposal) -> list[Proposal]:
    if proposal.op == "append":
        return [*proposals, proposal]
    kept = [item for item in proposals if item.field != proposal.field]
    kept.append(proposal)
    return kept


def handoff_read(root: Path | None = None) -> str:
    """Return the committed file. Never the draft."""
    path = _committed_path(_root(root))
    if not path.is_file():
        return "error: no committed handoff"
    return path.read_text(encoding="utf-8")


def handoff_propose(
    field: str,
    value: str,
    evidence: str,
    root: Path | None = None,
) -> str:
    """Append or replace one draft proposal. Does not touch the committed file."""
    directory = _root(root)
    if field not in FIELD_ORDER:
        return "error: unknown field"
    if "\n" in value or "\n" in evidence:
        return "error: value and evidence must be a single line"
    stored = value.strip()
    if stored == "":
        return "error: empty value"
    if field == "status" and stored not in STATUSES:
        return "error: status must be done, partial, or blocked"
    try:
        _load_record(directory)
        proposals = _load_proposals(directory)
    except HandoffError as exc:
        return f"error: {exc}"

    op = "append" if field in LIST_FIELDS else "replace"
    proposals = _upsert(
        proposals,
        Proposal(field=field, op=op, value=stored, evidence=evidence.strip()),
    )
    if field == "blocked" and stored != BLOCKED_SENTINEL:
        proposals = _upsert(
            proposals,
            Proposal(
                field="status",
                op="replace",
                value="blocked",
                evidence="set because blocked is not none",
            ),
        )
    _write_proposals(directory, proposals)
    return "ok: proposed"


def handoff_commit(approved: bool = False, root: Path | None = None) -> str:
    """Apply the draft only when a human has approved it."""
    if not approved:
        return "error: no human approval"
    directory = _root(root)
    try:
        record = _load_record(directory)
        proposals = _load_proposals(directory)
    except HandoffError as exc:
        return f"error: {exc}"
    if not proposals:
        return "error: empty draft"

    changed: set[str] = set()
    for proposal in proposals:
        if proposal.field not in FIELD_ORDER:
            return "error: draft has an unknown field"
        if proposal.field in LIST_FIELDS:
            if proposal.op != "append":
                return "error: list proposal must append"
            record.items(proposal.field).append(proposal.value)
        else:
            if proposal.op != "replace":
                return "error: scalar proposal must replace"
            if proposal.field == "status" and proposal.value not in STATUSES:
                return "error: status must be done, partial, or blocked"
            record.set_scalar(proposal.field, proposal.value)
        changed.add(proposal.field)

    _committed_path(directory).write_text(render_committed(record), encoding="utf-8")
    _write_proposals(directory, [])
    _append_audit(directory, "commit", changed)
    return "ok: committed"


def handoff_reject_draft(root: Path | None = None) -> str:
    """Discard the draft and leave the committed file unchanged."""
    directory = _root(root)
    try:
        proposals = _load_proposals(directory)
    except HandoffError as exc:
        return f"error: {exc}"
    changed = {proposal.field for proposal in proposals}
    _write_proposals(directory, [])
    _append_audit(directory, "reject", changed)
    return "ok: rejected"


def prompt_approval() -> bool:
    """Ask on a TTY. Anything other than ``approve``, including no TTY, is a reject."""
    if not sys.stdin.isatty():
        return False
    try:
        answer = input("approve or reject [reject]: ").strip().lower()
    except EOFError:
        return False
    return answer == "approve"


def register_mcp(server: object, root: Path) -> None:
    """Register the four tools. ``handoff_commit`` cannot approve."""
    tool = getattr(server, "tool")

    @tool(name="handoff_read")
    def mcp_read() -> str:
        """Return the committed handoff file."""
        return handoff_read(root)

    @tool(name="handoff_propose")
    def mcp_propose(field: str, value: str, evidence: str) -> str:
        """Propose one field. Does not modify the committed file."""
        return handoff_propose(field, value, evidence, root)

    @tool(name="handoff_commit")
    def mcp_commit() -> str:
        """Refuse. A human approves by running the CLI on a TTY."""
        handoff_commit(approved=False, root=root)
        return (
            "error: no human approval. A human must run "
            "`uv run python skills/handoff/scripts/handoff_mcp.py commit` "
            "on a TTY and answer approve."
        )

    @tool(name="handoff_reject_draft")
    def mcp_reject() -> str:
        """Discard the draft. The committed file stays unchanged."""
        return handoff_reject_draft(root)


def serve(root: Path | None = None) -> int:
    """Serve the tools over stdio when the MCP SDK imports."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        print(
            "mcp is not installed. The tool contract is the plain functions in this module.",
            file=sys.stderr,
        )
        return 1
    directory = _root(root)
    server = MCPServer("handoff")
    register_mcp(server, directory)
    server.run(transport="stdio")
    return 0


def _print_result(text: str) -> int:
    if text.startswith("error:"):
        print(text, file=sys.stderr)
        return 1
    sys.stdout.write(text if text.endswith("\n") or text == "" else text + "\n")
    return 0


def _take_root(argv: list[str]) -> tuple[Path | None, list[str]]:
    """Accept ``--root`` before or after the subcommand."""
    root: Path | None = None
    cleaned: list[str] = []
    index = 0
    while index < len(argv):
        if argv[index] == "--root" and index + 1 < len(argv):
            root = Path(argv[index + 1])
            index += 2
            continue
        cleaned.append(argv[index])
        index += 1
    return root, cleaned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Human-gated handoff record. --root PATH may appear before or after the subcommand.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("read", help="print the committed file")

    propose = sub.add_parser("propose", help="add one draft proposal")
    propose.add_argument("--field", required=True)
    propose.add_argument("--value", required=True)
    propose.add_argument("--evidence", default="")

    sub.add_parser("commit", help="apply the draft after a TTY approval")
    sub.add_parser("reject", help="discard the draft")
    sub.add_parser("serve", help="stdio MCP server, if the SDK imports")

    raw = list(sys.argv[1:] if argv is None else argv)
    chosen, cleaned = _take_root(raw)
    args = parser.parse_args(cleaned)
    root = chosen if chosen is not None else DEFAULT_ROOT
    if args.cmd == "read":
        return _print_result(handoff_read(root))
    if args.cmd == "propose":
        return _print_result(
            handoff_propose(args.field, args.value, args.evidence, root)
        )
    if args.cmd == "commit":
        return _print_result(handoff_commit(approved=prompt_approval(), root=root))
    if args.cmd == "reject":
        return _print_result(handoff_reject_draft(root))
    if args.cmd == "serve":
        return serve(root)
    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
