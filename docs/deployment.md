# Deployment guide

## Local

Use Docker Compose for an isolated demonstration:

```bash
cp .env.example .env
docker compose up --build
```

Replace every `local-development-only` secret before shared use.

## Production design requirements

- Managed PostgreSQL with TLS, backups, encryption, and least privilege.
- Private container registry with signed images and immutable digests.
- Secret manager integration; never repository or Compose defaults.
- Reverse proxy/API gateway with authentication, authorization, rate limits,
  request size limits, and audit logs.
- Separate read-only analytics role and no payment-system write credentials.
- Restricted network paths and private metrics endpoints.
- Immutable artifact version linking data, model, report, and deployment.
- Log redaction and data-retention policy.

## Health and observability

- Liveness: `/healthz`
- Readiness: `/readyz`
- Metrics: `/metrics`
- Prometheus rules: `observability/prometheus/alert-rules.yml`
- Runbooks: `docs/runbooks/`

## Rollback

Deploy versioned images. If validation fails, route traffic to the prior image,
retain analytical outputs for investigation, and do not delete the evidence
needed for reconciliation.
