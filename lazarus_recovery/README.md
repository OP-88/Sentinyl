# Lazarus Recovery - "Break Glass" Tor Backdoor

**Last-resort recovery system accessed via Tor Hidden Service with Shamir's Secret Sharing**

When your server is completely locked down (SSH blocked, firewall rules preventing access), Lazarus provides an emergency backdoor accessible only through Tor Client Authorization.

---

## 🚨 Security Model

**Threat Model Defense**:
- ✅ Port scanning → Hidden service (invisible)
- ✅ Unauthorized access → Tor client authorization (cryptographic key required)
- ✅ Brute force → 5-second delay + 3-attempt suicide switch
- ✅ Replay attacks → One-time shard reconstruction
- ✅ Timing attacks → Constant-time hash comparison

---

## Architecture

```
Admin (with 3 shards) → Tor Browser (with auth key) → Hidden Service
                                                            ↓
                                                     Flask (127.0.0.1:9999)
                                                            ↓
                                                     Shamir Reconstruction
                                                            ↓
                                            If valid: iptables -F (recovery)
                                            If 3 failures: systemctl stop tor (suicide)
```

**Components**:
1. **Shamirs Secret Sharing**: 32-byte Master Key split into 5 shards (any 3 recover)
2. **Tor Hidden Service**: v3 onion with client authorization (x25519)
3. **Flask Server**: Recovery interface with HTML form
4. **Suicide Switch**: 3 failed attempts = Tor service killed

---

## Quick Start

### 1. Initial Setup (One-Time)

```bash
cd lazarus_recovery

# Install dependencies
pip install -r requirements.txt

# Generate Master Key & Shards
python lazarus_setup.py
```

**Output**: 5 shards (write them down on paper!) + Tor configuration instructions

### 2. Configure Tor Hidden Service

Edit `/etc/tor/torrc`:

```
HiddenServiceDir /var/lib/tor/lazarus/
HiddenServicePort 80 127.0.0.1:9999
HiddenServiceVersion 3
```

Create client authorization file (from setup output):

```bash
sudo mkdir -p /var/lib/tor/lazarus/authorized_clients
sudo nano /var/lib/tor/lazarus/authorized_clients/admin.auth
# Paste: descriptor:x25519:<PUBLIC_KEY>
```

Restart Tor:

```bash
sudo systemctl restart tor
```

Get your onion address:

```bash
sudo cat /var/lib/tor/lazarus/hostname
```

### 3. Start Recovery Server

```bash
sudo python lazarus_server.py
```

Server runs on `127.0.0.1:9999` (Tor Hidden Service only).

### 4. Client Setup (Admin Machine)

Save the private key from setup:

```bash
mkdir -p ~/.tor/authorized_clients
echo "YOUR_PRIVATE_KEY" > ~/.tor/authorized_clients/lazarus.auth_private
```

Configure Tor Browser to use client authorization.

---

## Usage (Emergency Recovery)

### Scenario: Server Locked Out

You accidentally locked yourself out with strict iptables rules:

```bash
iptables -P INPUT DROP
iptables -A INPUT -p tcp --dport 22 -j DROP
```

SSH is now inaccessible. **Use Lazarus**:

### Recovery Steps

1. **Access via Tor Browser**:
   ```
   http://YOUR_ONION_ADDRESS.onion
   ```

2. **Provide ANY 3 shards** in the web form

3. **Wait 5 seconds** (anti-brute force delay)

4. **If valid**: Firewall flushed → SSH accessible again

5. **If invalid**: 
   - Attempt 1-2: Error message, remaining attempts shown
   - Attempt 3: **Tor service killed** (suicide switch activated)

---

## Security Features

### 1. Shamir's Secret Sharing (3-of-5)

**How it works**:
- Master Key (32 bytes) split into 5 shards
- **ANY 3 shards** can reconstruct the key
- Losing 2 shards is acceptable
- Losing 3+ shards = permanent lock (by design)

**Why this is secure**:
- Individual shards reveal ZERO information about the key
- Attacker needs 3+ shards (impossible if distributed)

### 2. Tor Client Authorization

**x25519 Keypair**:
- Server has public key (validates clients)
- Admin has private key (proves identity)
- Without private key, .**onion address is invisible**

**Benefits**:
- Hidden service unreachable to unauthorized users
- No port scanning attack surface
- Cryptographically enforced access control

### 3. Anti-Brute Force

**5-Second Delay**:
```python
time.sleep(5)  # Every request delayed
```

**Suicide Switch** (3 attempts):
```python
if failed_attempts >= 3:
    systemctl stop tor  # Service terminates
```

**Result**: Maximum 3 attempts before permanent shutdown.

### 4. Constant-Time Comparison

```python
secrets.compare_digest(reconstructed_hash, master_hash)
```

Prevents timing attacks (attacker cannot measure hash comparison speed).

---

## File Structure

```
lazarus_recovery/
├── lazarus_setup.py       # Key/shard generator
├── lazarus_server.py      # Flask recovery server
├── requirements.txt       # Dependencies
├── README.md             # This file
└── lazarus.hash          # Master key hash (generated)
```

---

## Security Considerations

### Shard Storage

🔐 **DO**:
- Write shards on **paper** (never digital)
- Store each shard in a **separate physical location**
- Use **safety deposit boxes, safes, trusted contacts**

❌ **DON'T**:
- Store shards digitally (USB, cloud, email)
- Keep all shards in one location
- Share shards via insecure channels

### Operational Security

1. **Test before emergency**: Verify recovery works in a non-critical environment
2. **Rotate keys annually**: Generate new shards periodically
3. **Monitor Tor logs**: Check for unauthorized access attempts
4. **Document procedure**: Ensure team knows how to use Lazarus

### Threat Model Limitations

**Lazarus CANNOT protect against**:
- Physical server access (attacker can reset via console)
- Kernel compromise (rootkit could bypass)
- Stolen shards (if attacker gets 3+ shards)

**Lazarus PROTECTS against**:
- Accidental lockout via misconfigured firewall
- Remote attacks (hidden service invisible)
- Brute force (suicide switch)

---

## Troubleshooting

### "Tor service not accessible"

**Check Tor is running**:
```bash
sudo systemctl status tor
```

**Check onion address**:
```bash
sudo cat /var/lib/tor/lazarus/hostname
```

### "Invalid shards" error

- Verify you're using shards from the **correct setup run**
- Check shard format: `1-abc123...` (index-hex)
- Ensure no typos (each character matters)

### "Permission denied" errors

Server must run as root:
```bash
sudo python lazarus_server.py
```

### Suicide switch activated

If 3 failures occurred, Tor is stopped. **Restart manually**:

```bash
sudo systemctl start tor
# Wait 30 seconds for hidden service to initialize
```

Server will be accessible again.

---

## Advanced Configuration

### Change Attempt Limit

Edit `lazarus_server.py`:

```python
class LazarusState:
    MAX_ATTEMPTS = 5  # Default: 3
```

### Custom Delay

```python
class LazarusState:
    DELAY_SECONDS = 10  # Default: 5
```

### Change Port

Edit `lazar us_server.py` and `torrc`:

```python
app.run(host='127.0.0.1', port=8888)
```

```
HiddenServicePort 80 127.0.0.1:8888
```

---

## Testing

### Test Locally (Without Tor)

1. Generate test keys:
   ```bash
   python lazarus_setup.py
   ```

2. Save the 3 shards shown

3. Start server:
   ```bash
   sudo python lazarus_server.py
   ```

4. Access locally:
   ```
   http://127.0.0.1:9999
   ```

5. Submit 3 valid shards → Should see success

6. Submit 3 invalid shards → Suicide switch activates

---

## Production Deployment

### systemd Service

Create `/etc/systemd/system/lazarus.service`:

```ini
[Unit]
Description=Lazarus Recovery Server
After=tor.service
Requires=tor.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sentinyl/lazarus_recovery
ExecStart=/usr/bin/python3 /opt/sentinyl/lazarus_recovery/lazarus_server.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable lazarus
sudo systemctl start lazarus
```

---

## Security Audit Checklist

- [ ] Shards stored securely (paper, separate locations)
- [ ] Tor client auth configured (private key on admin machine)
- [ ] Hidden service accessible only via Tor
- [ ] Suicide switch tested (3 failures = Tor stops)
- [ ] Master key NEVER saved (only hash exists)
- [ ] Server runs as root (for iptables)
- [ ] Logs reviewed for unauthorized attempts

---

## License

Part of the Sentinyl security platform.

---

**Lazarus Recovery: When everything else fails, rise from the ashes.** 🔥🔐
