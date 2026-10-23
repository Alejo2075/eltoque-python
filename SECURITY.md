# Security Policy

## Supported versions

Only the latest released version receives security fixes (pre-1.0).

## Reporting a vulnerability

**Please do not open a public issue.** Report privately through GitHub's
"Report a vulnerability" button (Security → Advisories) on this repository.

Include: affected version, a description, and a minimal reproduction **using a fake token**.
Never send a real elTOQUE token or provider data. We aim to acknowledge reports within a week.

## Scope

In scope: token leakage (logs, errors, `repr`), header injection, unsafe redirects,
resource exhaustion in the client, insecure defaults.

Out of scope: vulnerabilities in the elTOQUE service itself (report those to elTOQUE) and
leaks caused by an application printing its own token.

If you believe a token was exposed, ask elTOQUE to rotate it.

See also [docs/security.md](docs/security.md).
