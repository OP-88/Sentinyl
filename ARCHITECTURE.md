# Sentinyl Architecture: A Modular Approach to Digital Risk

## The Philosophy: Plug-and-Play Security

Security is not "One Size Fits All." A Fortune 500 company needs **Brand Protection**; a Freelance Developer needs **Server Protection**. Sentinyl uses a **Compartmentalized Architecture** to serve both.

**The Strategy**: Offer security as composable modules. Buy what you need, ignore the rest.

---

## 📦 Module A: Sentinyl Scout (The Watchtower)

**Type**: Passive / External  
**Installation**: None (SaaS-only)  
**Target Audience**: Everyone (Enterprises, SMBs, Individuals)

### The Role
This is the **baseline**. It looks **outward** at the internet to see who is impersonating you or leaking your data. It is the "eyes" of the operation.

### Features
- **Typosquatting Detection**: Monitors 50+ domain variations for malicious registrations
- **GitHub Leak Monitoring**: Scans public repositories for exposed credentials
- **Brand Reputation Checks**: Detects phishing sites and impostor domains
- **WHOIS Intelligence**: Tracks threat actor infrastructure
- **Neo4j Graph Analytics**: Visualizes relationships between domains, IPs, and repositories

### Value Proposition
**"Zero-Installation Risk Visibility"** - See external threats without touching your infrastructure.

### Who Needs This?
- Companies protecting brand reputation
- Security teams tracking domain squatters
- Compliance teams monitoring credential exposure
- Anyone concerned about external attack surface

---

## 📦 Module B: Sentinyl Guard (The Bunker)

**Type**: Active / Internal Agent  
**Installation**: Lightweight Python agent (`sentinyl_guard.py`)  
**Target Audience**: VPS Users, Dev Agencies, SaaS Startups ("The Under-Protected")

### The Gap It Fills

**The Problem**: Large enterprises use expensive EDR tools (CrowdStrike, SentinelOne, Carbon Black) costing $50-100 per endpoint. Small teams running VPS infrastructure usually have **nothing**.

**The Victims**: Developers running vulnerable stacks (Next.js, React, Node.js) on DigitalOcean, Linode, or AWS EC2 instances. They face:
- RCE exploits (e.g., "React2Next" vulnerabilities)
- Crypto-mining malware
- Reverse shell attacks
- C2 beacon installations

**The Traditional Solution**: Enterprise EDR requires:
- $10K+ annual licensing
- Dedicated SOC team
- Complex deployment
- Ongoing tuning and maintenance

**Sentinyl Guard**: "EDR Lite" for the mid-market gap. Powerful infrastructure protection for the small-scale builder.

### The Role
This is the optional **"Muscle."** It runs on your VPS and watches for "absurd behavior" that signatures miss.

### Features
- **Behavioral Monitoring**: Detects zero-day RCEs via anomaly detection
  - **Geo-Anomaly**: "Why is my server in NYC connecting to North Korea?"
  - **Process Anomaly**: "Why did `node` just spawn `/bin/sh`?" (Reverse Shell)
  - **Resource Anomaly**: "Why is CPU at 100% for 10 minutes?" (Crypto-mining)
- **Dead Man's Switch**: Automated `iptables` blocking if admin is unresponsive (5-min countdown)
- **Interactive Alerts**: Override via Teams/Slack action buttons
- **MITRE ATT&CK Mapping**: Contextualizes threats (T1059, T1071, T1496)

### Value Proposition
**"Early Warning for the SOC-less"** - Enterprise-grade threat detection without enterprise complexity.

### Who Needs This?
- Developers running production apps on VPS
- Startups that can't afford CrowdStrike
- Agencies managing client infrastructure
- Solo founders running SaaS products
- Anyone with servers but no security team

---

## 🏗️ Integration Logic: How the Modules Work Together

### Architectural Principle: **Autonomy at the Edge**

Sentinyl Guard operates **independently** on the VPS. It only contacts Sentinyl Core (Scout backend) when a **High-Fidelity Threat** is detected.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENTINYL PLATFORM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MODULE A: SENTINYL SCOUT (Core SaaS)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ☁️  External Threat Detection (No Installation)         │  │
│  │  • Typosquatting Scanner                                 │  │
│  │  • GitHub Leak Detector                                  │  │
│  │  • Brand Monitoring                                      │  │
│  │  • WHOIS Intelligence                                    │  │
│  │                                                          │  │
│  │  🎯 Customer: Everyone                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│                            ↕ (Optional API Integration)         │
│                                                                 │
│  MODULE B: SENTINYL GUARD (Edge Agent) [OPTIONAL]             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Deployed on: User's VPS Infrastructure                  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  VPS Instance (DigitalOcean/AWS/Linode)            │  │  │
│  │  │  ┌──────────────────────────────────────────────┐  │  │  │
│  │  │  │  sentinyl_guard_agent.py (Python)            │  │  │  │
│  │  │  │  • Behavioral Sensors (Geo/Process/Resource) │  │  │  │
│  │  │  │  • Dead Man's Switch                         │  │  │  │
│  │  │  │  • iptables Auto-Block                       │  │  │  │
│  │  │  └──────────────────────────────────────────────┘  │  │  │
│  │  │                       │                              │  │  │
│  │  │                       ↓ (Only when threat detected) │  │  │
│  │  │            API: POST /guard/alert                   │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                          │  │
│  │  🎯 Customer: VPS Operators without Enterprise EDR      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  INTEGRATION:                                                   │
│  • Guard sends alerts to Scout backend (FastAPI)               │
│  • Scout enriches with MITRE mapping & risk scoring            │
│  • Scout delivers via Teams/Slack with action buttons          │
│  • Admin responds → Guard polls for override → Executes block  │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Separation Matters

**For Scout-Only Users**:
- No infrastructure footprint
- No performance overhead
- No agent management
- Pure external visibility

**For Guard-Enabled Users**:
- External threats (Scout) + Internal threats (Guard) in one dashboard
- Unified alerting (all alerts go to same Teams/Slack channel)
- Single pane of glass for security posture
- Optional - can disable Guard without affecting Scout

**Technical Benefits**:
- **Decoupled**: Guard failure doesn't affect Scout
- **Scalable**: Can run 1000s of Guard agents without backend bottleneck (edge computing)
- **Flexible**: Customers choose their protection level
- **Upgradeable**: Scout customers can add Guard later with one command

---

## 💰 Business Model: Modular Pricing

| Tier | Scout | Guard | Price |
|------|-------|-------|-------|
| **Free** | 5 scans/month | ❌ | $0 |
| **Scout Pro** | Unlimited scans | ❌ | $49/month |
| **Guard Lite** | ❌ | 3 agents | $29/month |
| **Full Stack** | Unlimited scans | Unlimited agents | $99/month |

**The Pitch**: 
- Sell **just Scout** to brand-conscious enterprises
- Sell **just Guard** to dev agencies managing VPS fleets
- Sell **both** to security-mature startups

**Scalability**: No feature bloat. Customers pay for what they use.

---

## 🎯 Target Markets

### Scout-Only Customers
- **Fortune 500 Companies**: Brand protection, compliance scanning
- **Marketing Agencies**: Client domain monitoring
- **Legal Firms**: IP protection, trademark monitoring

### Guard-Only Customers
- **Dev Agencies**: Managing 50+ client VPS instances
- **Freelance Developers**: Personal project protection
- **Bootstrapped Startups**: Can't afford enterprise EDR

### Full-Stack Customers
- **SaaS Companies**: External brand + internal infrastructure
- **FinTech Startups**: Regulatory compliance + server security
- **Security-Conscious SMBs**: Complete risk visibility

---

## 🔍 The "Mid-Market Gap" Explained

```
┌──────────────────────────────────────────────────────────────┐
│              THE ENTERPRISE SECURITY MARKET                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  $10M+ ARR Companies                                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ✅ CrowdStrike EDR ($100/endpoint)                     │ │
│  │ ✅ Dedicated SOC Team                                  │ │
│  │ ✅ 24/7 Monitoring                                     │ │
│  │ ✅ Incident Response Retainers                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  THE GAP (Sentinyl Guard's Target)                         │
│  $100K-$2M ARR Companies / Solo Developers                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ❌ Can't afford $10K+ EDR licensing                    │ │
│  │ ❌ No SOC team                                         │ │
│  │ ❌ Basic monitoring only (CPU graphs, not threats)     │ │
│  │ ⚠️  Exposed to: RCE exploits, crypto-miners, C2       │ │
│  │                                                        │ │
│  │ 💡 SENTINYL GUARD FILLS THIS GAP                      │ │
│  │    - $29/month per agent                               │ │
│  │    - Zero SOC required (Dead Man's Switch automation)  │ │
│  │    - Behavioral detection (not signatures)             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  <$100K ARR / Hobbyists                                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ✅ Free tier: 3 Guard agents                          │ │
│  │ ✅ Basic Scout scanning                                │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation Structure

- **[README.md](README.md)**: Platform overview, quick start for Scout
- **[SENTINYL_GUARD.md](SENTINYL_GUARD.md)**: Guard technical deep-dive
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: This document (modular design)
- **[SLACK_INTEGRATION.md](SLACK_INTEGRATION.md)**: Notification setup

---

## 🚀 Getting Started

### I Just Want Brand Protection (Scout Only)
```bash
# No installation needed - use API
curl -X POST http://sentinyl.example.com/scan \
  -H "Content-Type: application/json" \
  -d '{"domain": "mycompany.com", "scan_type": "typosquat"}'
```

### I Need Server Protection (Guard Only)
```bash
# Install agent on your VPS
curl -fsSL http://sentinyl.example.com/install.sh | sudo bash
```

### I Want Both (Full Stack)
```bash
# Use Scout API + Install Guard agent
# All alerts unified in Teams/Slack
```

---

## 🎓 Philosophy: "Builder/Breaker" Mindset

Sentinyl was built by security engineers who understand:
- **Enterprise tools are overkill for small teams**
- **Free tools are insufficient for production**
- **The mid-market deserves enterprise-grade protection at startup pricing**

**Scout** gives you the visibility of a $100K threat intel platform.  
**Guard** gives you the protection of a $50K EDR solution.  
**Together**, they cost less than a Netflix subscription.

---

**Built for the 99% of companies who can't afford a dedicated security team.**
