# Security Policy

## Supported Scope

Security reports are welcome for the current default branch.

Please report issues involving:

- credential or secret exposure
- remote code execution
- auth/session weaknesses in the UI
- unsafe command execution or path traversal
- cross-boundary control-plane escalation
- data corruption of canonical project truth

## Reporting

Do not open a public issue for a suspected vulnerability.

Use GitHub private vulnerability reporting if it is enabled for this repository.
If it is not available, contact the maintainer through a private channel first
and include:

- affected file(s) and environment assumptions
- exact reproduction steps
- impact assessment
- any proof-of-concept artifacts

## Disclosure Expectations

- Give the maintainer reasonable time to reproduce and fix the issue before
  public disclosure.
- Avoid posting live secrets, private tokens, or personal identifiers in issues
  or pull requests.

## Hardening Expectations For Contributors

- Never commit `.env`, `conf/secrets.env`, API keys, tokens, or chat IDs.
- Prefer fail-closed behavior for auth and external integrations.
- Treat `/root/...`-style absolute paths as deployment defaults, not public API.
