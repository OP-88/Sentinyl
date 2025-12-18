# Ghost Protocol - Single Packet Authorization

**Cryptographic port knocking for invisible server access**

Ghost Protocol keeps admin ports (SSH, etc.) completely invisible to port scanners until receiving a valid encrypted "knock" packet.

## Features

✅ **Stealth Mode** - All ports appear "filtered" to Nmap/Shodan  
✅ **Authenticated Encryption** - PyNaCl (XSalsa20-Poly1305)  
✅ **Anti-Replay** - Timestamp validation (±10 seconds)  
✅ **IP Verification** - Prevents spoofing attacks  
✅ **Rate Limiting** - 1 knock per IP per 5 seconds  
✅ **Silent Operation** - Server never responds to invalid knocks  

---

## Architecture

```
┌─────────────┐                    ┌─────────────┐
│   Client    │   Encrypted UDP    │   Server    │
│             │ ───────────────────►│  (daemon)   │
│             │   Port 62201       │             │
└─────────────┘                    └─────┬───────┘
                                         │
                                   ┌─────▼────────┐
                                   │   iptables   │
                                   │   ipset      │
                                   └──────────────┘
```

**Workflow**:
1. Client encrypts: `TIMESTAMP:NONCE:CLIENT_IP`
2. Sends UDP packet to server:62201
3. Server validates (decrypt, timestamp check, IP verify)
4. Opens firewall for client IP (60 seconds)

---

## Quick Start

### 1. Generate Shared Secret

```bash
python ghost_keygen.py
```

Save the output and add to environment on **both** client and server:

```bash
export GHOST_SECRET_KEY='abc123...'
echo 'export GHOST_SECRET_KEY="abc123..."' >> ~/.bashrc
```

### 2. Server Setup

**Install dependencies**:
```bash
sudo pip install -r requirements.txt
```

**Create ipset** (one-time):
```bash
sudo ipset create ghost_whitelist hash:ip timeout 60
```

**Configure iptables**:
```bash
# Allow whitelisted IPs
sudo iptables -I INPUT -m set --match-set ghost_whitelist src -j ACCEPT

# Block SSH by default (port 22)
sudo iptables -A INPUT -p tcp --dport 22 -j DROP
```

**Start server**:
```bash
sudo python ghost_server.py --verbose
```

### 3. Client Usage

**Install dependencies**:
```bash
pip install pynacl
```

**Send knock**:
```bash
python ghost_client.py --server YOUR_SERVER_IP --verbose
```

**Connect to server**:
```bash
# Firewall is now open for 60 seconds
ssh user@YOUR_SERVER_IP
```

---

## Security Model

### Cryptography

- **Algorithm**: NaCl SecretBox (XSalsa20-Poly1305)
- **Encryption**: XSalsa20 stream cipher
- **Authentication**: Poly1305 MAC
- **Nonce**: 24 bytes random (crypto-secure)
- **Shared Secret**: 32 bytes (from environment)

### Anti-Replay Protection

**Timestamp Window**: ±10 seconds
- Rejects packets older than `now - 10s`
- Rejects future packets `now + 10s`
- **Requirement**: NTP sync on both client and server

### IP Verification

```python
# Server validates: packet source IP == claimed IP in payload
if packet_source_ip != payload_claimed_ip:
    reject()  # Prevents spoofing
```

### Rate Limiting

- Maximum 1 knock per IP per 5 seconds
- Prevents DoS attacks on server

---

## Usage Examples

### Basic Knock (Auto-Detect IP)

```bash
python ghost_client.py --server 203.0.113.5
```

### Manual IP (NAT/VPN Scenarios)

```bash
# Specify the IP that will appear at the server
python ghost_client.py --server 203.0.113.5 --ip 10.0.0.5
```

### Custom Port

```bash
# Server
sudo python ghost_server.py --port 12345

# Client
python ghost_client.py --server 203.0.113.5 --port 12345
```

### Verbose Logging

```bash
# See detailed packet information
python ghost_client.py -s 203.0.113.5 -v
```

---

## systemd Service (Production)

Create `/etc/systemd/system/ghost-protocol.service`:

```ini
[Unit]
Description=Ghost Protocol SPA Server
After=network.target

[Service]
Type=simple
User=root
Environment="GHOST_SECRET_KEY=YOUR_SECRET_HERE"
WorkingDirectory=/opt/sentinyl/ghost_protocol
ExecStart=/usr/bin/python3 /opt/sentinyl/ghost_protocol/ghost_server.py --port 62201
Restart=on-failure
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl enable ghost-protocol
sudo systemctl start ghost-protocol
sudo systemctl status ghost-protocol
```

---

## Troubleshooting

### "Permission denied" on server

Server requires root or `CAP_NET_RAW` + `CAP_NET_ADMIN`:

```bash
# Grant capabilities (non-root)
sudo setcap cap_net_raw,cap_net_admin=+ep /path/to/ghost_server.py
```

### "GHOST_SECRET_KEY not set"

Ensure environment variable is set:

```bash
export GHOST_SECRET_KEY='your_hex_key_here'
echo $GHOST_SECRET_KEY  # Verify
```

### "Timestamp out of range"

Cl and server clocks not synchronized:

```bash
# Install NTP
sudo apt install ntp
sudo systemctl start ntp
```

### Knock not working

1. **Check server logs**: `/var/log/ghost_protocol.log`
2. **Verify shared secret matches** on client and server
3. **Check firewall allows UDP port 62201**
4. **Test with verbose mode**: `--verbose` flag

---

## Security Best Practices

### Shared Secret Management

🔐 **DO**:
- Store in environment variables
- Use password manager for backup
- Rotate every 90 days
- Use different secrets for dev/prod

❌ **DON'T**:
- Hardcode in scripts
- Commit to version control
- Share via insecure channels

### Network Security

- Use VPN + Ghost Protocol for defense in depth
- Monitor knock attempts in logs
- Alert on excessive failed knocks
- Keep server time synchronized (NTP)

### Key Rotation

```bash
# Generate new key
python ghost_keygen.py

# Update on server
export GHOST_SECRET_KEY='new_key...'
systemctl restart ghost-protocol

# Update on all authorized clients
export GHOST_SECRET_KEY='new_key...'
```

---

## Testing

```bash
# Start server in one terminal
sudo python ghost_server.py --verbose

# Send knock in another terminal
python ghost_client.py --server 127.0.0.1 --verbose

# Expected output:
# [+] Knock sent successfully!
# Server log: ✓ VALID KNOCK from 127.0.0.1
```

---

## Files

- `ghost_keygen.py` - Generate shared secret
- `ghost_client.py` - Knock sender (runs on admin machine)
- `ghost_server.py` - Knock listener (runs on server)
- `requirements.txt` - Python dependencies
- `README.md` - This file

---

## References

- [PyNaCl Documentation](https://pynacl.readthedocs.io/)
- [Scapy Documentation](https://scapy.readthedocs.io/)
- [Single Packet Authorization Paper](https://www.cipherdyne.org/fwknop/docs/SPA.html)

---

**Warning**: Ghost Protocol is a defense-in-depth measure. Always use strong SSH keys, fail2ban, and regular security updates.

🛡️ **Ghost Protocol - Invisible until you knock.**
