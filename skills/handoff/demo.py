#!/usr/bin/env python3
"""Scripted proof of the handoff gate. No LLM and no network."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import handoff_mcp  # noqa: E402

SEED = """\
# Handoff
status: partial
goal: Sign the user in.
now: Login fails with an expired token.
decisions:
  - ask the user before retrying
rejected:
  - retry login with the same expired token
artifacts:
  - skills/handoff/demo.py
next: Propose a replacement auth approach.
blocked: none
"""

DECISION = "issue a new token instead of retrying"
DECISION_EVIDENCE = "user said the expired token must not be retried"
REJECTED = "refresh the session by replaying the expired token"
REJECTED_EVIDENCE = "same token returned 401 again"
BLOCKED = "need a human to pick the auth scheme"


def fail(name: str) -> None:
    print(f"FAIL: {name}")
    sys.exit(1)


def check(condition: bool, name: str) -> None:
    if not condition:
        fail(name)


def draft_value(text: str, field_name: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line != f"- field: {field_name}":
            continue
        for follow in lines[index + 1 : index + 4]:
            prefix = "  value: "
            if follow.startswith(prefix):
                return follow[len(prefix) :]
    return None


def main() -> int:
    root = handoff_mcp.DEFAULT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    (root / "HANDOFF.md").write_text(SEED, encoding="utf-8")
    (root / "HANDOFF.draft.md").write_text("", encoding="utf-8")
    (root / "audit.log").write_text("", encoding="utf-8")

    seeded = handoff_mcp.handoff_read(root)
    check(seeded == SEED, "seed read")
    check("retry login with the same expired token" in seeded, "seed rejected")

    proposed = handoff_mcp.handoff_propose(
        "decisions", DECISION, DECISION_EVIDENCE, root
    )
    check(proposed.startswith("ok:"), "propose decision")
    proposed = handoff_mcp.handoff_propose(
        "rejected", REJECTED, REJECTED_EVIDENCE, root
    )
    check(proposed.startswith("ok:"), "propose rejected")
    check(handoff_mcp.handoff_read(root) == seeded, "read still seeded")

    audit_before = (root / "audit.log").read_text(encoding="utf-8")
    refused = handoff_mcp.handoff_commit(approved=False, root=root)
    check(refused.startswith("error:"), "commit without approval")
    check(handoff_mcp.handoff_read(root) == seeded, "unapproved commit")
    check(
        (root / "audit.log").read_text(encoding="utf-8") == audit_before,
        "audit unchanged",
    )

    committed_result = handoff_mcp.handoff_commit(approved=True, root=root)
    check(committed_result.startswith("ok:"), "commit approved")
    committed = handoff_mcp.handoff_read(root)
    check(DECISION in committed, "new decision")
    check(REJECTED in committed, "new rejected")
    check(DECISION_EVIDENCE not in committed, "decision evidence omitted")
    check(REJECTED_EVIDENCE not in committed, "rejected evidence omitted")
    check((root / "HANDOFF.draft.md").read_text(encoding="utf-8").strip() == "", "draft cleared")
    check("retry login with the same expired token" in committed, "old rejected kept")

    approval_lines = (root / "audit.log").read_text(encoding="utf-8").splitlines()
    check(len(approval_lines) == 1, "one approval line")
    check("approved_by=human" in approval_lines[0], "approved_by human")

    blocked = handoff_mcp.handoff_propose("blocked", BLOCKED, "two schemes remain", root)
    check(blocked.startswith("ok:"), "propose blocked")
    draft = (root / "HANDOFF.draft.md").read_text(encoding="utf-8")
    check(draft_value(draft, "status") == "blocked", "proposed status blocked")
    check(handoff_mcp.handoff_read(root) == committed, "committed unchanged by propose")

    rejected = handoff_mcp.handoff_reject_draft(root)
    check(rejected.startswith("ok:"), "reject draft")
    check(handoff_mcp.handoff_read(root) == committed, "committed unchanged by reject")
    check((root / "HANDOFF.draft.md").read_text(encoding="utf-8").strip() == "", "draft empty after reject")
    audit_lines = (root / "audit.log").read_text(encoding="utf-8").splitlines()
    check(len(audit_lines) == 2, "approval plus rejection")
    check("approved_by=human" in audit_lines[0], "approval line remains")
    check(audit_lines[1].split()[1] == "reject", "rejection logged")

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
