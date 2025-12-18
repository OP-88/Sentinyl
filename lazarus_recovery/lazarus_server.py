#!/usr/bin/env python3
"""
Lazarus Recovery - Flask Server

"Break Glass" recovery interface accessible via Tor Hidden Service.
Validates Shamir shards and flushes iptables on success.

CRITICAL SECURITY:
- 3 failed attempts = Tor service killed (suicide switch)
- 5-second delay per request (anti-brute force)
- Constant-time hash comparison
- Input sanitization

Usage:
    sudo python lazarus_server.py

Requirements:
    - Must run as root (for iptables manipulation)
    - lazarus.hash file must exist
    - Tor Hidden Service configured
"""
import os
import sys
import time
import secrets
import hashlib
import subprocess
import re
from pathlib import Path

try:
    from flask import Flask, request, render_template_string, jsonify
except ImportError:
    print("ERROR: Flask not installed. Run: pip install flask", file=sys.stderr)
    sys.exit(1)

try:
    from shamirs import share, interpolate
except ImportError:
    print("ERROR: shamirs module not installed. Run: pip install shamirs", file=sys.stderr)
    sys.exit(1)


app = Flask(__name__)

# Global state (in-memory)
class LazarusState:
    """Global state for tracking attempts"""
    failed_attempts = 0
    MAX_ATTEMPTS = 3
    DELAY_SECONDS = 5
    
    # Load master hash on startup
    master_hash = None
    
    @classmethod
    def load_hash(cls, filepath="lazarus.hash"):
        """Load master key hash from file"""
        try:
            with open(filepath, 'r') as f:
                cls.master_hash = f.read().strip()
            print(f"[*] Loaded Master Key hash from {filepath}")
            return True
        except FileNotFoundError:
            print(f"ERROR: {filepath} not found. Run lazarus_setup.py first.", file=sys.stderr)
            return False
        except Exception as e:
            print(f"ERROR: Failed to load hash: {e}", file=sys.stderr)
            return False


# HTML template for recovery interface
RECOVERY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🔴 Lazarus Recovery</title>
    <style>
        body {
            background: #0a0a0a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            background: #1a1a1a;
            border: 2px solid #ff0000;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
        }
        h1 {
            color: #ff0000;
            text-align: center;
            font-size: 2em;
            margin-bottom: 20px;
            text-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
        }
        .warning {
            background: #2a0000;
            border: 1px solid #ff0000;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .warning h3 {
            margin-top: 0;
            color: #ff6666;
        }
        .shard-input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            background: #0a0a0a;
            border: 1px solid #00ff00;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border-radius: 5px;
        }
        .submit-btn {
            width: 100%;
            padding: 15px;
            background: #ff0000;
            color: #ffffff;
            border: none;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            border-radius: 5px;
            margin-top: 20px;
            transition: background 0.3s;
        }
        .submit-btn:hover {
            background: #cc0000;
        }
        .attempts {
            text-align: center;
            color: #ffaa00;
            margin-top: 15px;
            font-size: 14px;
        }
        label {
            display: block;
            margin-top: 15px;
            color: #00ff00;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔴 LAZARUS RECOVERY</h1>
        
        <div class="warning">
            <h3>⚠️ CRITICAL WARNING:</h3>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li>This is a LAST-RESORT recovery system</li>
                <li>Provide ANY 3 of your 5 Shamir shards</li>
                <li><strong>3 failed attempts = Service termination</strong></li>
                <li>5-second delay per request (anti-brute force)</li>
            </ul>
        </div>
        
        <form action="/recover" method="POST">
            <label for="shard1">Shard #1:</label>
            <input type="text" name="shard1" id="shard1" class="shard-input" 
                   placeholder="Enter first shard (hex string)" required>
            
            <label for="shard2">Shard #2:</label>
            <input type="text" name="shard2" id="shard2" class="shard-input" 
                   placeholder="Enter second shard (hex string)" required>
            
            <label for="shard3">Shard #3:</label>
            <input type="text" name="shard3" id="shard3" class="shard-input" 
                   placeholder="Enter third shard (hex string)" required>
            
            <button type="submit" class="submit-btn">🔓 RECOVER SYSTEM</button>
        </form>
        
        <div class="attempts">
            Attempts remaining: {{ 3 - attempts }} / 3
        </div>
    </div>
</body>
</html>
"""


def sanitize_shard(shard_input):
    """
    Sanitize shard input (must be valid shard format)
    
    Args:
        shard_input: Raw input string
        
    Returns:
        str: Sanitized shard or None if invalid
    """
    if not shard_input:
        return None
    
    # Trim whitespace
    shard_input = shard_input.strip()
    
    # Validate: shamirs library shards are in base64 format
    # Example: "ewAAAAIAAADIAf0D"
    pattern = r'^[A-Za-z0-9+/]+=*$'
    
    if not re.match(pattern, shard_input):
        return None
    
    return shard_input


def reconstruct_key(shards_list):
    """
    Reconstruct Master Key from shards
    
    Args:
        shards_list: List of 3 shard base64 strings
        
    Returns:
        bytes: Reconstructed key or None if invalid
    """
    try:
        # Convert base64 strings back to share objects
        shard_objects = [share.from_base64(s) for s in shards_list]
        
        # Interpolate to recover the secret integer
        reconstructed_int = interpolate(shard_objects)
        
        # Convert integer back to 32-byte key
        reconstructed_bytes = reconstructed_int.to_bytes(32, byteorder='big')
        
        return reconstructed_bytes
        
    except Exception as e:
        # Invalid shards (wrong format or insufficient)
        print(f"[!] Shard reconstruction failed: {e}")
        return None


def flush_firewall():
    """
    Flush all iptables rules (recovery action)
    
    Returns:
        bool: True if successful
    """
    try:
        # Set default policy to ACCEPT
        subprocess.run(
            ['iptables', '-P', 'INPUT', 'ACCEPT'],
            check=True,
            capture_output=True
        )
        
        # Flush all rules
        subprocess.run(
            ['iptables', '-F'],
            check=True,
            capture_output=True
        )
        
        print("[✓] SUCCESS: Firewall flushed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"[!] ERROR: Failed to flush firewall: {e.stderr}")
        return False
    except Exception as e:
        print(f"[!] ERROR: Unexpected error: {e}")
        return False


def kill_tor_service():
    """
    Stop Tor service (suicide switch)
    
    Returns:
        bool: True if successful
    """
    try:
        # Try systemctl first (modern Linux)
        result = subprocess.run(
            ['systemctl', 'stop', 'tor'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[🔴] CRITICAL: Tor service stopped via systemctl")
            return True
        
        # Fallback: service command (older Linux)
        result = subprocess.run(
            ['service', 'tor', 'stop'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[🔴] CRITICAL: Tor service stopped via service")
            return True
        
        print(f"[!] WARNING: Failed to stop Tor: {result.stderr}")
        return False
        
    except Exception as e:
        print(f"[!] ERROR: Failed to kill Tor: {e}")
        return False


@app.route('/')
def index():
    """Display recovery form"""
    return render_template_string(
        RECOVERY_TEMPLATE,
        attempts=LazarusState.failed_attempts
    )


@app.route('/recover', methods=['POST'])
def recover():
    """
    Process recovery request
    
    Returns:
        JSON response with status
    """
    # ANTI-BRUTE FORCE: 5-second delay
    print(f"[*] Recovery attempt received. Enforcing {LazarusState.DELAY_SECONDS}s delay...")
    time.sleep(LazarusState.DELAY_SECONDS)
    
    try:
        # Extract shards from form
        shard1 = request.form.get('shard1', '')
        shard2 = request.form.get('shard2', '')
        shard3 = request.form.get('shard3', '')
        
        # Sanitize inputs
        shard1 = sanitize_shard(shard1)
        shard2 = sanitize_shard(shard2)
        shard3 = sanitize_shard(shard3)
        
        # Validate all shards present
        if not all([shard1, shard2, shard3]):
            LazarusState.failed_attempts += 1
            print(f"[!] Invalid shard format. Attempts: {LazarusState.failed_attempts}/{LazarusState.MAX_ATTEMPTS}")
            
            # Check suicide threshold
            if LazarusState.failed_attempts >= LazarusState.MAX_ATTEMPTS:
                print("[🔴] CRITICAL: Maximum attempts reached. Triggering suicide switch...")
                kill_tor_service()
                return jsonify({
                    "status": "error",
                    "message": "SERVICE TERMINATED. Maximum attempts exceeded."
                }), 403
            
            remaining = LazarusState.MAX_ATTEMPTS - LazarusState.failed_attempts
            return jsonify({
                "status": "error",
                "message": f"INVALID SHARD FORMAT. {remaining} attempts remaining."
            }), 400
        
        # Reconstruct key
        print("[*] Reconstructing key from shards...")
        reconstructed_bytes = reconstruct_key([shard1, shard2, shard3])
        
        if not reconstructed_bytes:
            LazarusState.failed_attempts += 1
            print(f"[!] Key reconstruction failed. Attempts: {LazarusState.failed_attempts}/{LazarusState.MAX_ATTEMPTS}")
            
            # Check suicide threshold
            if LazarusState.failed_attempts >= LazarusState.MAX_ATTEMPTS:
                print("[🔴] CRITICAL: Maximum attempts reached. Triggering suicide switch...")
                kill_tor_service()
                return jsonify({
                    "status": "error",
                    "message": "SERVICE TERMINATED. Maximum attempts exceeded."
                }), 403
            
            remaining = LazarusState.MAX_ATTEMPTS - LazarusState.failed_attempts
            return jsonify({
                "status": "error",
                "message": f"INVALID SHARDS. {remaining} attempts remaining."
            }), 400
        
        # Hash the reconstructed key (now bytes, not hex)
        reconstructed_hash = hashlib.sha256(reconstructed_bytes).hexdigest()
        
        # CONSTANT-TIME COMPARISON (prevents timing attacks)
        if secrets.compare_digest(reconstructed_hash, LazarusState.master_hash):
            # SUCCESS - Flush firewall
            print("[✓] Valid shards! Executing recovery...")
            
            if flush_firewall():
                # Reset attempts on success
                LazarusState.failed_attempts = 0
                
                return jsonify({
                    "status": "success",
                    "message": "SUCCESS: FIREWALL FLUSHED. System recovered."
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": "ERROR: Failed to flush firewall (check logs)"
                }), 500
        else:
            # FAILURE - Invalid shards
            LazarusState.failed_attempts += 1
            print(f"[!] Invalid shards (hash mismatch). Attempts: {LazarusState.failed_attempts}/{LazarusState.MAX_ATTEMPTS}")
            
            # Check suicide threshold
            if LazarusState.failed_attempts >= LazarusState.MAX_ATTEMPTS:
                print("[🔴] CRITICAL: Maximum attempts reached. Triggering suicide switch...")
                kill_tor_service()
                return jsonify({
                    "status": "error",
                    "message": "SERVICE TERMINATED. Maximum attempts exceeded."
                }), 403
            
            remaining = LazarusState.MAX_ATTEMPTS - LazarusState.failed_attempts
            return jsonify({
                "status": "error",
                "message": f"INVALID SHARDS. {remaining} attempts remaining."
            }), 401
        
    except Exception as e:
        # Unexpected error - don't increment counter (could be server issue)
        print(f"[!] Unexpected error: {e}")
        return jsonify({
            "status": "error",
            "message": "INTERNAL ERROR. Check server logs."
        }), 500


def check_root():
    """Verify running as root"""
    if os.geteuid() != 0:
        print("ERROR: This script must be run as root (for iptables)", file=sys.stderr)
        print("Run: sudo python lazarus_server.py", file=sys.stderr)
        return False
    return True


def main():
    """Main entry point"""
    print("=" * 70)
    print("Lazarus Recovery - Flask Server")
    print("=" * 70)
    print()
    
    # Check root
    if not check_root():
        return 1
    
    # Load master hash
    if not LazarusState.load_hash():
        return 1
    
    print()
    print("[*] Server Configuration:")
    print(f"    - Listen: 127.0.0.1:9999 (Tor Hidden Service)")
    print(f"    - Max Attempts: {LazarusState.MAX_ATTEMPTS}")
    print(f"    - Delay per request: {LazarusState.DELAY_SECONDS}s")
    print(f"    - Suicide switch: ENABLED")
    print()
    print("=" * 70)
    print("🔴 CRITICAL: This is a LAST-RESORT recovery system")
    print("=" * 70)
    print()
    print("[*] Starting Flask server...")
    print("[*] Access via Tor Hidden Service only")
    print()
    
    # Run Flask app
    try:
        app.run(
            host='127.0.0.1',
            port=9999,
            debug=False  # NEVER use debug in production!
        )
    except KeyboardInterrupt:
        print("\n[*] Server shutdown")
        return 0
    except Exception as e:
        print(f"ERROR: Server failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
