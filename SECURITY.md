# Security Policy

## Supported Versions

| Version | Supported |
|:--------|:----------|
| 0.1.x   | ✅ Active  |

## Architecture Security Guarantees

This system is designed for **air-gapped, local-first government deployment**. The following security properties are architecturally enforced:

1. **Zero Cloud Data Transmission** — All citizen data, grievance records, government orders, and official documents are processed and stored exclusively on the local machine. No external API calls are made for data processing.

2. **AST Execution Sandbox** — Natural language data queries are parsed through Python's `ast` module and validated against a strict allowlist before execution. The following are blocked at the AST level:
   - `import` statements
   - `exec()`, `eval()`, `compile()` calls
   - `open()`, `os.*`, `sys.*`, `subprocess.*` access
   - Any mutation operations on DataFrames

3. **Deterministic Aadhaar PII Redaction** — All 12-digit numbers are validated against the Verhoeff checksum algorithm. Valid Aadhaar numbers are masked (`XXXXXXXX1234`) before database persistence.

4. **Anti-Hallucination Verification Barrier** — AI-generated content is fact-checked against document fingerprints. Generic or ungrounded phrases are blocked.

5. **Officer-Gated Communications** — Outbound emails are never sent autonomously. All communications require explicit officer review and approval.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

### How to Report

- **Email**: [naveencmy76@gmail.com](mailto:naveencmy76@gmail.com)
- **Subject line**: `[SECURITY] Erode Collectorate AI — <brief description>`

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

### Response Timeline

| Action | Timeline |
|:---|:---|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix release (if confirmed) | Within 14 business days |

### Scope

The following are **in scope** for security reports:

- AST sandbox bypass or code injection
- PII (Aadhaar) redaction bypass
- Unauthorized data exfiltration
- Authentication or authorization bypass
- SQL injection in database operations

The following are **out of scope**:

- Denial of service on the local machine
- Issues requiring physical access to the deployment machine
- Social engineering attacks

## Disclosure Policy

We follow a **coordinated disclosure** policy. Please do not publicly disclose vulnerabilities until a fix has been released and affected deployments have been notified.
