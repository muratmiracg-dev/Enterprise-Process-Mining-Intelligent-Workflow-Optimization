# Security policy

## Supported version

Security fixes are applied to the latest `main` revision.

## Reporting

Do not open a public issue for a suspected vulnerability or exposed secret.
Use GitHub's private vulnerability reporting for this repository.

Include the affected component, reproduction steps, impact, and a safe proof of
concept. Never include real payment, supplier, employee, or credential data.

## Design controls

- The public API is read-only.
- The container runs as an unprivileged user with dropped capabilities.
- Compose mounts analytical outputs read-only.
- Database credentials are environment-provided and examples are development-only.
- CodeQL, dependency updates, and filesystem vulnerability scanning run in CI.
- Prediction results cannot authorize or execute a payment.

See `docs/security-threat-model.md` for boundaries and residual risks.
