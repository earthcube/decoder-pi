# Handoff
status: partial
goal: Sign the user in.
now: Login fails with an expired token.
decisions:
  - ask the user before retrying
  - issue a new token instead of retrying
rejected:
  - retry login with the same expired token
  - refresh the session by replaying the expired token
artifacts:
  - skills/handoff/demo.py
next: Propose a replacement auth approach.
blocked: none
