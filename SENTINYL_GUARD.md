# Automating Defense: The "Dead Man's Switch" for Cloud Infrastructure

## The Problem: Silence is Deadly

In modern Cloud Security, the most dangerous threat isn't the noisy DDoS attack; it's the **silent compromise**. 

Vulnerabilities in frameworks like Next.js (often called "React2Next" exploits) allow attackers to achieve **Remote Code Execution (RCE)**. Once inside, they don't crash your server; they install a "listener" (Reverse Shell) or a crypto-miner and stay quiet.

Traditional firewalls only block **incoming** traffic. They rarely stop your own server from "phoning home" to a Command & Control (C2) server in a hostile jurisdiction.

**The danger**: By the time you notice abnormal network activity in logs (if you're even checking), your brand reputation is already being destroyed from the inside out.

---

## The Solution: Sentinyl Guard (Active Defense)

We don't rely on passive logs. We implement an **Active Watchdog** that lives on the VPS. It operates on a **"Zero Trust" model** for outbound traffic.

### 1. The Sensor: Behavioral Anomaly Detection

Instead of scanning for known malware files (signatures), we scan for **"Absurd Behavior."**

#### Geo-Fencing
The agent checks **every established network connection**. If your server in Nairobi connects to an IP in Russia or North Korea, that is an **anomaly**.

**How it works:**
- Uses `psutil` to monitor all network connections
- Queries `ipinfo.io` API for real-time geolocation
- Flags connections to high-risk countries: Russia, China, North Korea, Iran, Belarus, Syria, Venezuela
- Bypasses trusted IPs (configurable whitelist)

**Example:**
```python
# Agent detects: VPS in US → Outbound connection to 185.220.101.1 (Russia)
# Verdict: GEO-ANOMALY (CRITICAL)
```

####Process Lineage
We monitor the **node process**. A web server should never spawn a shell (`/bin/bash`). If it does, it's a confirmed RCE attempt.

**How it works:**
- Monitors web server processes: `node`, `python`, `nginx`, `apache2`
- Checks for child processes
- Detects if any child is a shell: `bash`, `sh`, `zsh`, `dash`
- Flags parent → shell spawning as reverse shell indicator

**Example:**
```python
# Agent detects: node (PID 1234) → /bin/bash (PID 5678)
# Verdict: PROCESS-ANOMALY (CRITICAL) - Reverse Shell
```

#### Resource Abuse Detection
We detect **sustained high CPU usage** that indicates crypto-mining.

**How it works:**
- Establishes baseline CPU usage on startup
- Monitors for CPU > 90% for extended periods
- Flags 40%+ deviation from baseline
- Identifies top CPU-consuming process

**Example:**
```python
# Agent detects: CPU at 95% (baseline: 15%) for 5+ minutes
# Top process: [xmrig] (crypto-miner)
# Verdict: RESOURCE-ANOMALY (HIGH)
```

---

### 2. The Logic: The Dead Man's Switch

**Manual response is too slow.** If a hacker gets root, they will disable your logging tools within minutes. We reverse the advantage.

#### The Workflow

1. **The Trigger**: When an anomaly is detected, the Agent creates a "Pending Block" state.

2. **The Timer**: It starts a strict **5-minute countdown**.

3. **The Alert**: It pushes a "CRITICAL ALERT" card to Microsoft Teams with a **"MARK AS SAFE"** button.

4. **The Execution**: If the timer hits zero and no signal is received from the API, the Agent executes a "Self-Preservation" command:

```bash
# ONLY blocks the suspicious remote IP - NOT your admin SSH connection!
# Example: If your server connects to 185.220.101.1 (Russia), we block THAT IP only
iptables -A INPUT -s [SUSPICIOUS_IP] -j DROP
iptables -A OUTPUT -d [SUSPICIOUS_IP] -j DROP
```

**Important**: This blocks **only the suspicious connection** (e.g., the C2 server in Russia). Your SSH access from your laptop, your monitoring tools, your legitimate API clients - **none of these are affected**. The agent only blocks the specific IP that triggered the anomaly.

#### Admin Safety Guarantees

✅ **Your SSH connection is safe** - We never block port 22 from trusted sources  
✅ **Your management tools are safe** - Whitelist your office IP in `TRUSTED_IPS`  
✅ **Legitimate traffic is safe** - Only blocks the anomaly trigger IP  
✅ **You can override** - Click "MARK AS SAFE" in Teams/Slack to cancel block

#### Admin Safety Guarantees

✅ **Your SSH connection is safe** - We never block port 22 from trusted sources  
✅ **Your management tools are safe** - Whitelist your office IP in `TRUSTED_IPS`  
✅ **Legitimate traffic is safe** - Only blocks the anomaly trigger IP  
✅ **You can override** - Click "MARK AS SAFE" in Teams/Slack to cancel block

#### What Gets Blocked vs What Stays Safe

**Scenario 1: Geo-Anomaly Detected**
```
Your VPS (NYC) → Suspicious connection to 185.220.101.1 (Russia)
BLOCKED: 185.220.101.1 ONLY
SAFE: Your SSH from home (203.0.113.50), office VPN, monitoring tools, etc.
```

**Scenario 2: No Anomaly**
```
Your VPS (NYC) → You SSH from home (203.0.113.50)
BLOCKED: Nothing
SAFE: Everything - agent doesn't trigger on normal admin activity
```

**Scenario 3: False Positive**
```
Your VPS → Legitimate service in Russia (e.g., Yandex API)
BLOCKED: Would block if you don't respond
SAFE: Click "MARK AS SAFE" in Teams → Connection allowed
OR: Add IP to TRUSTED_IPS whitelist before deployment
```

#### Why This Works

This architecture **assumes the admin might be asleep, offline, or distracted**. By default, the system chooses **Safety**. 

**It is better to accidentally block a legitimate weird connection than to allow a C2 beacon to remain active for 8 hours while you sleep.**

#### Admin Override

The admin receives a rich notification in Teams/Slack with two options:

- **✅ MARK AS SAFE**: Cancels the countdown, no blocking occurs
- **🛑 CONFIRM BLOCK**: Immediately executes iptables block

If no action is taken, the agent auto-blocks after 5 minutes.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         VPS Instance                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Sentinyl Guard Agent                                     │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐│  │
│  │  │ Geo-Anomaly    │  │ Process        │  │ Resource     ││  │
│  │  │ Sensor         │  │ Anomaly Sensor │  │ Sensor       ││  │
│  │  │ (ipinfo.io)    │  │ (psutil)       │  │ (CPU/Mem)    ││  │
│  │  └────────┬───────┘  └───────┬────────┘  └──────┬───────┘│  │
│  │           └────────────┬──────┴──────────────────┘        │  │
│  │                        ↓                                   │  │
│  │           ┌────────────────────────────┐                  │  │
│  │           │  Dead Man's Switch         │                  │  │
│  │           │  - 5 min countdown         │                  │  │
│  │           │  - Poll for override       │                  │  │
│  │           │  - Execute iptables block  │                  │  │
│  │           └────────────┬───────────────┘                  │  │
│  └────────────────────────┼────────────────────────────────────┘  │
└────────────────────────────┼───────────────────────────────────┘
                             │ HTTPS
                             ↓
        ┌────────────────────────────────────────────────┐
        │         Sentinyl SaaS (Backend)                │
        │  ┌──────────────────────────────────────────┐  │
        │  │  POST /guard/alert                       │  │
        │  │  ← Agent sends anomaly                   │  │
        │  └──────────────┬───────────────────────────┘  │
        │                 ↓                               │
        │  ┌──────────────────────────────────────────┐  │
        │  │  Redis Queue: queue:guard                │  │
        │  └──────────────┬───────────────────────────┘  │
        │                 ↓                               │
        │  ┌──────────────────────────────────────────┐  │
        │  │  Guard Alert Worker                      │  │
        │  │  - Enrich with MITRE ATT&CK              │  │
        │  │  - Calculate risk score                  │  │
        │  │  - Build Adaptive Card                   │  │
        │  └──────────────┬───────────────────────────┘  │
        │                 ↓                               │
        │  ┌──────────────────────────────────────────┐  │
        │  │  Teams/Slack Notifier                    │  │
        │  │  ┌────────────────────────────────────┐  │  │
        │  │  │ 🚨 CRITICAL ALERT                  │  │  │
        │  │  │ Geo-Anomaly: Russia Connection     │  │  │
        │  │  │ ⏱️ Auto-block in 4:32               │  │  │
        │  │  │ [✅ MARK AS SAFE] [🛑 BLOCK]       │  │  │
        │  │  └────────────────────────────────────┘  │  │
        │  └──────────────┬───────────────────────────┘  │
        └─────────────────┼──────────────────────────────┘
                          │
                          ↓ Webhook callback
        ┌──────────────────────────────────────────────┐
        │  POST /guard/response                        │
        │  ← Admin clicks button                       │
        │  - Store decision in database                │
        └──────────────────────────────────────────────┘
                          ↑
                          │ Polling
                          │
        ┌──────────────────────────────────────────────┐
        │  GET /guard/status/{agent_id}                │
        │  → Agent polls for override                  │
        │  ← Returns: admin_response, should_block     │
        └──────────────────────────────────────────────┘
```

---

## Tech Stack

### Agent (VPS-side)
- **Python 3.8+** - Core runtime
- **psutil** - System process monitoring
- **requests** - HTTP client for API communication
- **subprocess** - iptables command execution
- **ipinfo.io API** - Real-time IP geolocation

### Backend (SaaS)
- **FastAPI** - REST API framework
- **PostgreSQL** - Relational database for events
- **Redis** - Message queue for worker processing
- **SQLAlchemy** - ORM for database models

### Workers
- **Python** - Worker runtime
- **Smart Alert System** - MITRE ATT&CK mapping, risk scoring
- **Teams/Slack Notifiers** - Multi-channel notification delivery

---

## Installation

### Quick Start (One-Line Install)

On your VPS, run:

```bash
curl -fsSL http://your-sentinyl-api.com/install.sh | sudo bash -s -- \
  --api-url http://your-sentinyl-api.com \
  --agent-id $(uuidgen)
```

### Manual Installation

1. **Install dependencies:**
```bash
apt-get update
apt-get install -y python3 python3-pip
pip3 install psutil requests
```

2. **Download agent:**
```bash
mkdir -p /opt/sentinyl-guard
cd /opt/sentinyl-guard
wget https://github.com/OP-88/Sentinyl/raw/main/agent/sentinyl_guard_agent.py
chmod +x sentinyl_guard_agent.py
```

3. **Create systemd service:**
```bash
cat > /etc/systemd/system/sentinyl-guard.service << EOF
[Unit]
Description=Sentinyl Guard Active Defense Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/sentinyl-guard/sentinyl_guard_agent.py \
  --api-url http://your-api.com \
  --agent-id YOUR-AGENT-ID
Restart=always
RestartSec=10

# Security capabilities
AmbientCapabilities=CAP_NET_ADMIN
CapabilityBoundingSet=CAP_NET_ADMIN

[Install]
WantedBy=multi-user.target
EOF
```

4. **Start service:**
```bash
systemctl daemon-reload
systemctl enable sentinyl-guard
systemctl start sentinyl-guard
```

5. **Verify:**
```bash
systemctl status sentinyl-guard
journalctl -u sentinyl-guard -f
```

---

## Configuration

### Customize High-Risk Countries

Edit `sentinyl_guard_agent.py`:

```python
HIGH_RISK_COUNTRIES = [
    "Russia", "China", "North Korea", "Iran",
    "Belarus", "Syria", "Venezuela"
    # Add more countries as needed
]
```

### Whitelist Trusted IPs

**CRITICAL**: Add your admin IPs BEFORE deployment to prevent false positives:

```python
TRUSTED_IPS = [
    "8.8.8.8",          # Google DNS
    "1.1.1.1",          # Cloudflare DNS
    "203.0.113.50",     # 🔑 YOUR OFFICE IP - Add this!
    "198.51.100.0/24",  # 🔑 YOUR VPN SUBNET - Add this!
    "your-cdn-ip",      # Your CDN provider
    # Add ANY IP you legitimately connect to
]
```

**Why this matters**: If you use a Russian VPN for testing, or have a legitimate service in China, whitelist those IPs to avoid blocking yourself during troubleshooting.

### Adjust Countdown Timer

Default is 5 minutes. To change:

```python
COUNTDOWN_DURATION = 600  # 10 minutes
```

### Scan Interval

Default is 30 seconds. To change:

```bash
python3 sentinyl_guard_agent.py --poll-interval 60  # Scan every 60 seconds
```

---

## MITRE ATT&CK Mapping

Sentinyl Guard maps behavioral anomalies to MITRE techniques:

| Anomaly Type | MITRE Technique | Tactic |
|--------------|----------------|--------|
| Geo-Anomaly | T1071.001 - Application Layer Protocol: Web Protocols | Command and Control |
| Process Anomaly | T1059 - Command and Scripting Interpreter | Execution |
| Resource Anomaly | T1496 - Resource Hijacking | Impact |

---

## Monitoring & Logs

### View Agent Logs
```bash
journalctl -u sentinyl-guard -f
```

### Check Database for Events
```bash
docker-compose exec db psql -U sentinyl -d sentinyldb
```

```sql
-- View recent guard events
SELECT 
    hostname, 
    anomaly_type, 
    severity, 
    target_ip, 
    target_country,
    admin_response, 
    blocked,
    created_at 
FROM guard_events 
JOIN guard_agents ON guard_events.agent_id = guard_agents.id
ORDER BY created_at DESC 
LIMIT 10;
```

### View Active Agents
```sql
SELECT 
    id, 
    hostname, 
    ip_address, 
    last_heartbeat, 
    active 
FROM guard_agents 
WHERE active = true;
```

---

## Troubleshooting

### Agent Not Starting

**Check logs:**
```bash
journalctl -u sentinyl-guard -n 50
```

**Common issues:**
- Python dependencies missing: `pip3 install psutil requests`
- API URL unreachable: Verify network connectivity
- Permissions issue: Agent must run as root for iptables

### Alerts Not Appearing in Teams

**Verify webhook:**
```bash
curl -X POST https://your-teams-webhook-url \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message"}'
```

**Check worker logs:**
```bash
docker-compose logs worker | grep guard
```

### False Positives

If legitimate traffic is being flagged:

1. Add IPs to `TRUSTED_IPS` whitelist
2. Remove country from `HIGH_RISK_COUNTRIES`
3. Adjust thresholds in sensor logic

---

## Security Considerations

### Agent Privileges

The agent **requires root** for iptables execution. Security measures:
- Runs as systemd service with capability restrictions (`CAP_NET_ADMIN` only)
- No remote code execution capability
- All actions logged in systemd journal

### API Authentication

> [!WARNING]
> Initial implementation has **no API authentication**. For production:
> - Add API key header validation
> - Implement JWT tokens
> - Use HTTPS/TLS for all communication

### Network Segmentation

- Agent communicates only with Sentinyl API
- iptables rules block only suspicious IPs, not all traffic
- Whitelisting prevents blocking critical infrastructure

---

## Performance Impact

**CPU Usage:** ~0.5% average (psutil monitoring)  
**Memory:** ~50MB resident  
**Network:** Minimal (only API calls when anomalies detected)  
**Storage:** Logs rotated, ~100MB max

---

## Roadmap

- [ ] Machine learning for adaptive baseline detection
- [ ] Integration with threat intelligence feeds (AlienVault OTX, VirusTotal)
- [ ] Automated incident response playbooks
- [ ] Docker container monitoring
- [ ] Kubernetes cluster protection

---

## License

GPL-3.0 License - See [LICENSE](../LICENSE) file for details

---

**Built with ❤️ for DevOps Teams Who Don't Sleep**

*"When your infrastructure is under attack at 3 AM, let Sentinyl Guard have your back."*
