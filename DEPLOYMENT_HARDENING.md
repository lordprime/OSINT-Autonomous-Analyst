# OSINT Autonomous Analyst - Deployment Hardening Guide

## Agent 6: Security & Compliance Verification

This manual outlines the hardening steps required before moving to production environment.

### 1. Infrastructure Hardening

- [ ] **Docker Secrets**: Move all sensitive environment variables from `.env` to Docker Secrets for Swarm/K8s deployment.
- [ ] **Network Isolation**: Ensure `oaa_network` is internal only, exposing only port 80/443 via reverse proxy (Nginx).
- [ ] **Database Limiting**:
  - Neo4j: Disable remote code execution plugins if not used.
  - Redis: Enable strict AUTH and rename dangerous commands (`FLUSHALL`, `KEYS`).
  - Elasticsearch: Enable TLS for transport layer.

### 2. Application Security

- [ ] **JWT Key Rotation**: Implement automated rotation for `SECRET_KEY`.
- [ ] **Rate Limiting**: Verify Redis-backed rate limiting is active and blocking abusive IPs.
- [ ] **Input Sanitization**: Ensure Pydantic models leverage `constr` (constrained strings) to reject injection characters.

### 3. Compliance & Audit Verification

- [ ] **Immunability Check**: Verify TimescaleDB `audit_log` cannot be updated/deleted by the application user.
  ```sql
  -- Try to delete a log
  DELETE FROM audit_log WHERE log_id = '...';
  -- Should fail with: "Modification of audit logs prohibited"
  ```
- [ ] **PII Redaction**: Verify `ComplianceEngine` is redacting SSNs/CCs in logs.

### 4. OpSec Validation

- [ ] **Proxy Leak Test**:
  - Run `Agent 3` collection against [https://amiunique.org](https://amiunique.org) verify real IP is hidden.
  - Verify User-Agent matches top 50 browsers.
  - Verify Referer header is stripped.

### 5. Red Team Verification

Run the automated Red Team suite:
```bash
python -m tests.security.red_team
```
**Success Criteria**:
- ✅ Prompt Injection attempts blocked/ignored
- ✅ GDPR/PII collection attempts denied
- ✅ Denied actions successfully logged

---

**Authorized By**: Agent 6 (OAA_SecOps)
**Date**: 2026-01-12
