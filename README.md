# Sentinyl 🛡️

**B2B Digital Risk Protection & External Attack Surface Management Platform**

Sentinyl automates the "Reconnaissance" phase of ethical hacking to protect companies from external threats. Built on the Builder/Breaker philosophy, it uses software engineering principles to execute offensive security tasks at scale.

## 🎯 Features

### 🌐 Typosquatting Detection
- Generates 50+ domain variations using DNSTwist-like permutation logic
- Character omission, repetition, transposition
- Homoglyph substitution and keyboard typo simulation
- TLD variations and subdomain prefixes
- Real-time DNS resolution to detect active threats
- Automated WHOIS lookups for threat intelligence

### 🔍 GitHub Leak Detection
- Scans GitHub repositories for exposed credentials
- Searches for passwords, API keys, secrets, and tokens
- Intelligent severity classification
- Rate limit handling with exponential backoff
- Repository metadata extraction

### 📢 Real-time Notifications
- Slack webhook integration with rich Block Kit formatting
- Severity-based notifications (LOW, MEDIUM, HIGH, CRITICAL)
- Interactive alerts with action buttons for critical threats
- Detailed threat and leak reporting with repository links

## 🏗️ Architecture

Sentinyl follows a **microservices architecture** with worker-queue pattern:

```
Client → FastAPI → Redis Queue → Workers → PostgreSQL → Slack
```

### Components

1. **API Service** (FastAPI)
   - Accepts scan requests
   - Manages job dispatch
   - Provides result retrieval endpoints

2. **Message Queue** (Redis)
   - Buffers pending jobs
   - Ensures fault tolerance
   - Separate queues per scan type

3. **Worker Swarm** (Python)
   - Typosquatting engine
   - Leak detection scanner
   - Horizontally scalable

4. **Database** (PostgreSQL)
   - Stores scan results
   - Maintains threat intelligence
   - Tracks job history

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- (Optional) GitHub Personal Access Token
- (Optional) Slack Webhook URL for alerts

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/OP-88/Sentinyl.git
   cd Sentinyl
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your credentials
   ```

   Required variables:
   - `POSTGRES_PASSWORD` - Database password
   - `GITHUB_TOKEN` - GitHub API token (for leak detection)
   - `SLACK_WEBHOOK_URL` - Incoming webhook URL (for alerts)

3. **Start the platform**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are healthy**
   ```bash
   docker-compose ps
   ```

   All services should show "healthy" status.

5. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 📖 API Usage

### Initiate a Typosquatting Scan

```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "scan_type": "typosquat",
    "priority": "high"
  }'
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "domain": "example.com",
  "scan_type": "typosquat",
  "status": "pending",
  "message": "Scan job created and queued for processing"
}
```

### Initiate a Leak Detection Scan

```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "yourcompany.com",
    "scan_type": "leak",
    "priority": "critical"
  }'
```

### Retrieve Scan Results

```bash
curl http://localhost:8000/results/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "domain": "example.com",
  "job_type": "typosquat",
  "status": "completed",
  "started_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:35:00",
  "threats": [
    {
      "id": "...",
      "malicious_domain": "examp1e.com",
      "threat_type": "typosquat",
      "severity": "high",
      "ip_address": "192.0.2.1",
      "discovered_at": "2024-01-15T10:32:00"
    }
  ]
}
```

### Platform Statistics

```bash
curl http://localhost:8000/stats
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_PASSWORD` | PostgreSQL password | ✅ |
| `GITHUB_TOKEN` | GitHub API token | ⚠️ Recommended |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook | ⚠️ For alerts |
| `DATABASE_URL` | Override database URL | ❌ |
| `REDIS_URL` | Override Redis URL | ❌ |

### Getting API Tokens

**GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select `public_repo` or `repo` scope
4. Copy token to `.env`

**Slack Webhook:**
1. Go to https://api.slack.com/messaging/webhooks
2. Click "Create your Slack app" or use existing app
3. Enable "Incoming Webhooks"
4. Click "Add New Webhook to Workspace"
5. Select channel for alerts (#security-alerts recommended)
6. Copy webhook URL to `.env`

**Detailed Guide:** See [SLACK_INTEGRATION.md](SLACK_INTEGRATION.md) for complete setup instructions and alert examples.

## 🐳 Docker Commands

### View logs
```bash
docker-compose logs -f api      # API logs
docker-compose logs -f worker   # Worker logs
docker-compose logs -f db       # Database logs
```

### Restart services
```bash
docker-compose restart api
docker-compose restart worker
```

### Scale workers
```bash
docker-compose up -d --scale worker=3
```

### Stop platform
```bash
docker-compose down
```

### Reset everything (⚠️ deletes data)
```bash
docker-compose down -v
docker-compose up -d
```

## 📊 Database Access

Connect to PostgreSQL directly:

```bash
docker-compose exec db psql -U sentinyl -d sentinyldb
```

View threats:
```sql
SELECT malicious_domain, severity, ip_address, discovered_at 
FROM threats 
WHERE is_active = true 
ORDER BY discovered_at DESC;
```

View leaks:
```sql
SELECT repository_name, leak_type, severity, discovered_at 
FROM github_leaks 
ORDER BY discovered_at DESC;
```

## 🛡️ Security Considerations

### API Security
- **Production deployment:** Add authentication middleware
- **CORS:** Configure `allow_origins` in `backend/main.py`
- **Rate limiting:** Implement request throttling

### Secrets Management
- Never commit `.env` file to Git
- Use Docker secrets in production
- Rotate API tokens regularly

### Network Security
- Deploy behind reverse proxy (nginx/Caddy)
- Enable HTTPS/TLS
- Use firewall rules to restrict access

## 🔍 Worker Details

### Typosquatting Worker
**Queue:** `queue:typosquat`

**Permutation Types:**
- Character omission (company → compay)
- Character repetition (company → commpany)
- Character transposition (company → comapny)
- Homoglyph substitution (company → c0mpany)
- Keyboard typos (company → companu)
- TLD variations (.com → .net, .org)
- Hyphenation (company → com-pany)
- Subdomain prefixes (www-company, secure-company)

**Output:** Active domains with IP addresses and nameservers

### Leak Detection Worker
**Queue:** `queue:leak`

**Search Keywords:**
- password
- api_key / apikey
- secret / secret_key
- token / access_token
- credentials
- private_key

**Rate Limits:**
- Authenticated: 5,000 requests/hour
- Unauthenticated: 60 requests/hour

## 📈 Scaling

### Horizontal Scaling
Run multiple worker instances:
```bash
docker-compose up -d --scale worker=5
```

### Vertical Scaling
Increase resources in `docker-compose.yml`:
```yaml
worker:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

## 🧪 Development

### Local Development (without Docker)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and Redis**
   ```bash
   # Use Docker for dependencies only
   docker-compose up -d db redis
   ```

3. **Run API**
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

4. **Run workers**
   ```bash
   python -m workers.typosquat_worker &
   python -m workers.leak_worker &
   ```

## 📝 License

GPL-3.0 License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 👤 Author

**OP-88**

## 📧 Support

For bugs and feature requests, please create an issue on GitHub.

---

**Built with ❤️ for IT Security Teams**

*Enterprise-grade Digital Risk Protection with Graph Analytics, Risk Scoring & Threat Intelligence*
