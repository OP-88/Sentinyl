# Security Guidelines - Sentinyl Project

## 🚨 SECRET MANAGEMENT PROTOCOL

### PRIMARY DIRECTIVE
**You are prohibited from committing or implementing hardcoded secrets, API keys, tokens, or passwords.**

---

## DEVELOPMENT RULES

### 1. Environment Variables Only

**❌ NEVER DO THIS:**
```python
# BAD - Hardcoded secret
stripe.api_key = "sk_live_abc123..."
GITHUB_TOKEN = "ghp_xyz789..."
DATABASE_URL = "postgresql://user:password@localhost/db"
```

**✅ ALWAYS DO THIS:**
```python
# GOOD - Environment variables
from backend.config import settings

stripe.api_key = settings.STRIPE_API_KEY
github_token = settings.GITHUB_TOKEN
database_url = settings.DATABASE_URL
```

### 2. Pydantic Settings for Configuration

All configuration must use `pydantic-settings` with environment variable validation:

```python
# backend/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    STRIPE_API_KEY: str  # Required
    GITHUB_TOKEN: Optional[str] = None  # Optional
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 3. The .gitignore Rule

**MANDATORY**: All projects must have `.env` in `.gitignore`:

```gitignore
# Environment Variables (CRITICAL!)
.env
.env.local
.env.*.local
*.env
secrets/

# API Keys
stripe_*
github_token*
webhook_*
*.pem
*.key
```

### 4. The .env.example Template

Provide a `.env.example` with **placeholder values**:

```bash
# .env.example
STRIPE_API_KEY=sk_test_YOUR_KEY_HERE
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
```

**NEVER include real values in .env.example!**

---

## DETECTION PATTERNS

### Dangerous String Patterns

Scan for these patterns before committing:

| Pattern | Type | Example |
|---------|------|---------|
| `sk_live_*` | Stripe Live Key | `sk_live_abc123...` |
| `sk_test_*` | Stripe Test Key | `sk_test_xyz789...` |
| `ghp_*` | GitHub Token | `ghp_abcdef...` |
| `whsec_*` | Webhook Secret | `whsec_123456...` |
| `postgres://` | Database URL | `postgresql://user:pass@host/db` |
| `Basic <base64>` | HTTP Basic Auth | `Authorization: Basic dXNlcjpwYXNz` |

### Pre-Commit Hook (Recommended)

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check for common secret patterns
if git diff --cached | grep -E "(sk_live_|sk_test_|ghp_|whsec_|postgres://.*:.*@)"; then
    echo "🚨 ERROR: Potential secret detected in staged files!"
    echo "Remove secrets and use environment variables instead."
    exit 1
fi
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## CODE REVIEW CHECKLIST

Before approving any PR, verify:

- [ ] No hardcoded API keys or tokens
- [ ] All secrets use `settings.VARIABLE_NAME`
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` exists with placeholders
- [ ] `config.py` uses Pydantic Settings
- [ ] No database credentials in code
- [ ] No webhook URLs hardcoded

---

## INCIDENT RESPONSE

### If a Secret is Committed

**IMMEDIATE ACTIONS (within 5 minutes):**

1. **Revoke the exposed secret immediately**
   - Stripe: Delete API key in Dashboard
   - GitHub: Revoke token in Settings
   - Database: Rotate password

2. **Remove from Git history**
   ```bash
   # Use BFG Repo-Cleaner
   java -jar bfg.jar --replace-text passwords.txt repo.git
   
   # Or git filter-branch (slower)
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch path/to/file' \
     --prune-empty --tag-name-filter cat -- --all
   
   git push origin --force --all
   ```

3. **Notify the team**
   - Send security alert
   - Document incident
   - Update runbook

4. **Audit for exposure**
   - Check access logs
   - Review Stripe/GitHub audit trails
   - Monitor for unauthorized usage

### Prevention

- Enable GitHub secret scanning
- Use [gitleaks](https://github.com/gitleaks/gitleaks) locally
- Implement pre-commit hooks
- Regular security audits

---

## SECRETS MANAGEMENT TOOLS

### Development (Local)

- **`.env` files**: For local development only
- **direnv**: Auto-load environment variables per directory
- **dotenv**: Python library to load `.env` files

### Production

| Tool | Use Case | Cost |
|------|----------|------|
| **AWS Secrets Manager** | AWS infrastructure | ~$0.40/secret/month |
| **Google Secret Manager** | GCP infrastructure | ~$0.06/secret/month |
| **HashiCorp Vault** | Multi-cloud, self-hosted | Free (OSS) / Enterprise |
| **Doppler** | Team secret management | Free - $12/user/month |
| **1Password Secrets** | Dev teams | $7.99/user/month |

### Recommended Setup (Sentinyl)

**Development**:
```bash
# .env (local only, gitignored)
STRIPE_API_KEY=sk_test_...
```

**Staging/Production**:
```bash
# Use Docker secrets or cloud provider
docker secret create stripe_key /path/to/key
```

Or environment injection:
```yaml
# docker-compose.yml
services:
  api:
    environment:
      - STRIPE_API_KEY=${STRIPE_API_KEY}
```

---

## TEAM ONBOARDING

### New Developer Setup

1. Clone repo
2. Copy environment template:
   ```bash
   cp .env.example .env
   ```
3. Request secrets from team lead (via 1Password/Doppler)
4. **NEVER** share secrets via:
   - ❌ Email
   - ❌ Slack/Teams messages
   - ❌ Screenshots
   - ❌ Git commits

✅ **USE**: Encrypted password manager, secure secret sharing tool

---

## AUTOMATED SCANNING

### GitHub Actions Workflow

```yaml
# .github/workflows/security-scan.yml
name: Secret Scanning

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Gitleaks Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Pre-Commit Framework

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

Install:
```bash
pip install pre-commit
pre-commit install
```

---

## MONITORING

### Enable GitHub Advanced Security

1. Repository Settings → Security & Analysis
2. Enable:
   - Secret scanning
   - Push protection
   - Dependency review

### Stripe Security Alerts

- Enable webhook signature verification
- Monitor API key usage in Dashboard
- Set up usage alerts

### Database Security

- Rotate passwords every 90 days
- Use read-only replicas where possible
- Enable SSL/TLS for connections
- Audit access logs

---

## COMPLIANCE

### Required for Production

- [ ] All secrets in secrets manager (not `.env`)
- [ ] API keys rotated every 90 days
- [ ] Audit logging enabled
- [ ] Least privilege access (IAM roles)
- [ ] Encrypted at rest (database)
- [ ] Encrypted in transit (TLS 1.3+)
- [ ] Secret scanning enabled
- [ ] Incident response plan documented

---

## REFERENCES

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [Stripe API Keys Best Practices](https://stripe.com/docs/keys)
- [12-Factor App: Config](https://12factor.net/config)

---

**Remember**: A single exposed API key can cost thousands in unauthorized usage or lead to data breaches. **When in doubt, rotate the secret.**

🔐 **Security is not optional. It's mandatory.**
