#!/usr/bin/env python3
"""
Ghost Protocol - Knock Client

Sends an encrypted UDP packet to open server firewall access.
Uses PyNaCl (libsodium) for authenticated encryption.

Single Packet Authorization (SPA) - the server remains completely invisible
until receiving a valid cryptographic "knock".

Usage:
    python ghost_client.py --server 203.0.113.5 --port 62201
    python ghost_client.py -s 203.0.113.5 -p 62201 --ip 10.0.0.5

Security:
    - Shared secret from environment variable (GHOST_SECRET_KEY)
    - Random nonce prevents replay attacks
    - Timestamp validation (±10 seconds)
    - No response expected (stealth mode)
"""
import argparse
import socket
import sys
import time
import os
from datetime import datetime

try:
    import nacl.secret
    import nacl.utils
    from nacl.encoding import HexEncoder
except ImportError:
    print("ERROR: PyNaCl not installed. Run: pip install pynacl", file=sys.stderr)
    sys.exit(1)


class GhostClient:
    """Ghost Protocol knock client"""
    
    def __init__(self, shared_secret_hex: str):
        """
        Initialize Ghost Protocol client
        
        Args:
            shared_secret_hex: 32-byte shared secret (hex-encoded)
        
        Raises:
            ValueError: If shared secret is invalid
        """
        try:
            # Convert hex secret to bytes
            secret_bytes = bytes.fromhex(shared_secret_hex)
            
            if len(secret_bytes) != 32:
                raise ValueError("Shared secret must be exactly 32 bytes")
            
            # Initialize NaCl SecretBox (XSalsa20-Poly1305)
            self.box = nacl.secret.SecretBox(secret_bytes)
            
        except Exception as e:
            raise ValueError(f"Invalid shared secret: {e}")
    
    def create_knock_packet(self, client_ip: str) -> bytes:
        """
        Create encrypted knock packet
        
        Packet structure (before encryption):
            TIMESTAMP:NONCE:CLIENT_IP
        
        Args:
            client_ip: Client's IP address to whitelist
            
        Returns:
            bytes: Encrypted packet payload
        """
        # Current Unix timestamp (seconds)
        timestamp = int(time.time())
        
        # Generate random nonce (24 bytes for XSalsa20)
        # This prevents rainbow table attacks and ensures uniqueness
        nonce_bytes = nacl.utils.random(24)
        nonce_hex = nonce_bytes.hex()
        
        # Construct plaintext payload
        plaintext = f"{timestamp}:{nonce_hex}:{client_ip}"
        
        # Encrypt with authenticated encryption
        # SecretBox automatically handles nonce generation and MAC
        ciphertext = self.box.encrypt(plaintext.encode('utf-8'))
        
        return ciphertext
    
    def send_knock(self, server_ip: str, port: int, client_ip: str) -> bool:
        """
        Send knock packet to server
        
        Args:
            server_ip: Target server IP
            port: Target UDP port (typically 62201)
            client_ip: Client IP to whitelist
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Create encrypted packet
            packet = self.create_knock_packet(client_ip)
            
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Set timeout (not expecting a response, but fail fast)
            sock.settimeout(1)
            
            # Send packet (fire-and-forget)
            sock.sendto(packet, (server_ip, port))
            
            # Close socket
            sock.close()
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to send knock: {e}", file=sys.stderr)
            return False


def get_local_ip() -> str:
    """
    Auto-detect local IP address
    
    Returns:
        str: Local IP address
    """
    try:
        # Create temporary socket to determine outbound IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ghost Protocol - Send encrypted knock to open server access",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic knock (auto-detect client IP)
  python ghost_client.py --server 203.0.113.5
  
  # Specify client IP manually (for NAT/VPN scenarios)
  python ghost_client.py --server 203.0.113.5 --ip 10.0.0.5
  
  # Custom port
  python ghost_client.py -s 203.0.113.5 -p 12345

Environment:
  GHOST_SECRET_KEY    32-byte shared secret (hex-encoded, required)
        """
    )
    
    parser.add_argument(
        '-s', '--server',
        required=True,
        help='Target server IP address'
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=62201,
        help='Target UDP port (default: 62201)'
    )
    
    parser.add_argument(
        '-i', '--ip',
        dest='client_ip',
        default=None,
        help='Client IP to whitelist (auto-detect if not specified)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Get shared secret from environment
    shared_secret = os.environ.get('GHOST_SECRET_KEY')
    
    if not shared_secret:
        print("ERROR: GHOST_SECRET_KEY environment variable not set", file=sys.stderr)
        print("Run: export GHOST_SECRET_KEY='your_32byte_hex_key'", file=sys.stderr)
        return 1
    
    # Auto-detect client IP if not specified
    client_ip = args.client_ip or get_local_ip()
    
    if args.verbose:
        print(f"[*] Ghost Protocol - Knock Client")
        print(f"[*] Target: {args.server}:{args.port}")
        print(f"[*] Client IP: {client_ip}")
        print(f"[*] Timestamp: {datetime.now().isoformat()}")
        print()
    
    try:
        # Initialize client
        client = GhostClient(shared_secret)
        
        # Send knock
        if args.verbose:
            print(f"[*] Sending encrypted knock...")
        
        success = client.send_knock(args.server, args.port, client_ip)
        
        if success:
            if args.verbose:
                print(f"[+] Knock sent successfully!")
                print(f"[+] Firewall should open for 60 seconds")
                print()
            return 0
        else:
            print("[-] Failed to send knock", file=sys.stderr)
            return 2
            
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
