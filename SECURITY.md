# Security Policy

## Supported versions

Only the latest release on PyPI and the `main` branch receive fixes.

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them
privately through GitHub's
[private vulnerability reporting](https://github.com/vincentkoc/dexscraper/security/advisories/new)
for this repository. Include the affected version, a description of the
impact and steps to reproduce.

## Scope

Security-relevant areas include:

- parsing of untrusted binary WebSocket frames (`protocol.py`,
  `enhanced_protocol.py`)
- the Cloudflare bypass path and any cookies or headers it handles
- files written by `--output`
- vulnerable runtime dependencies (`websockets`, `cloudscraper`, `requests`)

dexscraper is an unofficial client for public DexScreener data; it handles no
credentials of its own.
