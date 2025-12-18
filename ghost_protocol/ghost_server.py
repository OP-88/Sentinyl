#!/usr/bin/env python3
"""
Ghost Protocol - Knock Server Daemon

Listens for encrypted UDP packets and opens firewall access for authenticated clients.
Uses scapy for packet sniffing (bypasses firewall DROP rules).

Single Packet Authorization (SPA) - keeps admin ports invisible until valid knock received.

Usage:
    sudo python ghost_server.py --port 62201
    sudo python ghost_server.py -p 62201 --verbose

Security:
    - Shared secret from environment variable (GHOST_SECRET_KEY)
    - Timestamp validation (±10 seconds anti-replay)
    - IP verification (prevents spoofing)
    - Silent failure (no responses to invalid packets)
    - Rate limiting (1 knock per IP per 5 seconds)

Requires:
    - Root or CAP_NET_RAW capability for packet sniffing
    - CAP_NET_ADMIN for ipset manipulation
"""
import argparse
import sys
import os
import time
import subprocess
import logging
from datetime import datetime
from collections import defaultdict

try:
    from scapy.all import sniff, UDP, IP, Raw
except ImportError:
    print("ERROR: Scapy not installed. Run: pip install scapy", file=sys.stderr)
    sys.exit(1)

try:
    import nacl.secret
    import nacl.utils
    from nacl.encoding import HexEncoder
    import nacl.exceptions
except ImportError:
    print("ERROR: PyNaCl not installed. Run: pip install pynacl", file=sys.stderr)
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ghost_protocol.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('GhostServer')


class GhostServer:
    """Ghost Protocol knock server"""
    
    # Rate limiting: Track last knock time per IP
    knock_times = defaultdict(float)
    
    # Timestamp tolerance (seconds)
    TIMESTAMP_TOLERANCE = 10
    
    # Rate limit window (seconds)
    RATE_LIMIT_WINDOW = 5
    
    # Whitelist duration (seconds)
    WHITELIST_DURATION = 60
    
    def __init__(self, shared_secret_hex: str, verbose: bool = False):
        """
        Initialize Ghost Protocol server
        
        Args:
            shared_secret_hex: 32-byte shared secret (hex-encoded)
            verbose: Enable verbose logging
        
        Raises:
            ValueError: If shared secret is invalid
        """
        self.verbose = verbose
        
        try:
            # Convert hex secret to bytes
            secret_bytes = bytes.fromhex(shared_secret_hex)
            
            if len(secret_bytes) != 32:
                raise ValueError("Shared secret must be exactly 32 bytes")
            
            # Initialize NaCl SecretBox (XSalsa20-Poly1305)
            self.box = nacl.secret.SecretBox(secret_bytes)
            
            if self.verbose:
                logger.info("Ghost Protocol server initialized")
            
        except Exception as e:
            raise ValueError(f"Invalid shared secret: {e}")
    
    def validate_knock(self, ciphertext: bytes, source_ip: str) -> tuple[bool, str]:
        """
        Validate encrypted knock packet
        
        Args:
            ciphertext: Encrypted packet payload
            source_ip: Source IP from packet header
            
        Returns:
            tuple: (is_valid, client_ip)
        """
        try:
            # Decrypt payload
            plaintext = self.box.decrypt(ciphertext).decode('utf-8')
            
            # Parse payload: TIMESTAMP:NONCE:CLIENT_IP
            parts = plaintext.split(':')
            
            if len(parts) != 3:
                if self.verbose:
                    logger.warning(f"Invalid payload format from {source_ip}")
                return False, None
            
            timestamp_str, nonce_hex, claimed_ip = parts
            
            # Validate timestamp (anti-replay)
            try:
                knock_timestamp = int(timestamp_str)
                current_timestamp = int(time.time())
                time_delta = abs(current_timestamp - knock_timestamp)
                
                if time_delta > self.TIMESTAMP_TOLERANCE:
                    if self.verbose:
                        logger.warning(
                            f"Timestamp out of range from {source_ip}: "
                            f"delta={time_delta}s (max={self.TIMESTAMP_TOLERANCE}s)"
                        )
                    return False, None
                    
            except ValueError:
                if self.verbose:
                    logger.warning(f"Invalid timestamp from {source_ip}")
                return False, None
            
            # Verify source IP matches claimed IP (anti-spoofing)
            if source_ip != claimed_ip:
                logger.warning(
                    f"IP mismatch from {source_ip}: claimed={claimed_ip}"
                )
                return False, None
            
            # Check rate limiting
            last_knock_time = self.knock_times.get(source_ip, 0)
            if time.time() - last_knock_time < self.RATE_LIMIT_WINDOW:
                if self.verbose:
                    logger.warning(
                        f"Rate limit exceeded for {source_ip} "
                        f"(max 1 knock per {self.RATE_LIMIT_WINDOW}s)"
                    )
                return False, None
            
            # Update knock time
            self.knock_times[source_ip] = time.time()
            
            # All checks passed
            return True, claimed_ip
            
        except nacl.exceptions.CryptoError:
            # Decryption failed - wrong key or corrupted packet
            # Silent failure (don't log to prevent log spam)
            return False, None
            
        except Exception as e:
            # Unexpected error - log but don't crash
            if self.verbose:
                logger.error(f"Error validating knock from {source_ip}: {e}")
            return False, None
    
    def open_firewall(self, ip: str):
        """
        Add IP to firewall whitelist
        
        Args:
            ip: IP address to whitelist
        """
        try:
            # Use ipset to add IP with timeout
            # Command: ipset add ghost_whitelist <ip> timeout <duration>
            
            cmd = [
                'ipset', 'add', 'ghost_whitelist',
                ip, 'timeout', str(self.WHITELIST_DURATION),
                '-exist'  # Don't fail if IP already in set
            ]
            
            # UNCOMMENT FOR PRODUCTION:
            # result = subprocess.run(
            #     cmd,
            #     check=True,
            #     capture_output=True,
            #     text=True
            # )
            
            # FOR TESTING: Just print the command
            logger.info(f"[FIREWALL] Would execute: {' '.join(cmd)}")
            logger.info(f"[FIREWALL] Opening access for {ip} for {self.WHITELIST_DURATION} seconds")
            
            # Production logging:
            # logger.info(f"Whitelisted {ip} for {self.WHITELIST_DURATION} seconds")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to whitelist {ip}: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error whitelisting {ip}: {e}")
    
    def handle_packet(self, packet):
        """
        Handle incoming UDP packet
        
        This is called by scapy for each packet matching the BPF filter.
        All exceptions are caught to prevent daemon crash.
        
        Args:
            packet: Scapy packet object
        """
        try:
            # Verify packet has required layers
            if not packet.haslayer(IP) or not packet.haslayer(UDP) or not packet.haslayer(Raw):
                return
            
            # Extract source IP and payload
            source_ip = packet[IP].src
            payload = bytes(packet[Raw].load)
            
            if self.verbose:
                logger.debug(f"Received packet from {source_ip} ({len(payload)} bytes)")
            
            # Validate knock
            is_valid, client_ip = self.validate_knock(payload, source_ip)
            
            if is_valid:
logger.info(f"✓ VALID KNOCK from {client_ip}")
                self.open_firewall(client_ip)
            else:
                # Silent failure for invalid knocks (stealth mode)
                pass
                
        except Exception as e:
            # Catch all exceptions to prevent daemon crash
            if self.verbose:
                logger.error(f"Error handling packet: {e}")
    
    def start(self, port: int, interface: str = None):
        """
        Start listening for knock packets
        
        Args:
            port: UDP port to listen on
            interface: Network interface (None = all interfaces)
        """
        logger.info(f"=" * 70)
        logger.info(f"Ghost Protocol Server - Starting")
        logger.info(f"=" * 70)
        logger.info(f"Listening on UDP port {port}")
        if interface:
            logger.info(f"Interface: {interface}")
        logger.info(f"Timestamp tolerance: ±{self.TIMESTAMP_TOLERANCE} seconds")
        logger.info(f"Rate limit: 1 knock per {self.RATE_LIMIT_WINDOW} seconds")
        logger.info(f"Whitelist duration: {self.WHITELIST_DURATION} seconds")
        logger.info(f"=" * 70)
        logger.info("Ready to receive knock packets...")
        logger.info("")
        
        # BPF filter: Only UDP packets on specified port
        bpf_filter = f"udp and port {port}"
        
        try:
            # Start packet sniffing
            # This runs indefinitely, calling handle_packet for each matching packet
            sniff(
                filter=bpf_filter,
                prn=self.handle_packet,
                iface=interface,
                store=False  # Don't store packets in memory
            )
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise


def check_capabilities():
    """
    Check if running with required capabilities
    
    Returns:
        bool: True if has required capabilities
    """
    # Check if running as root
    if os.geteuid() == 0:
        return True
    
    # Check for CAP_NET_RAW capability (required for packet sniffing)
    # Note: This is a simplified check. In production, use libcap2-bin
    logger.warning("Not running as root. Packet sniffing may fail.")
    logger.warning("Grant capabilities with: sudo setcap cap_net_raw,cap_net_admin=+ep ghost_server.py")
    
    return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ghost Protocol - Knock server daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server on default port
  sudo python ghost_server.py
  
  # Custom port with verbose logging
  sudo python ghost_server.py --port 12345 --verbose
  
  # Specific network interface
  sudo python ghost_server.py --interface eth0

Environment:
  GHOST_SECRET_KEY    32-byte shared secret (hex-encoded, required)

Setup (one-time):
  # Create ipset
  sudo ipset create ghost_whitelist hash:ip timeout 60
  
  # Add iptables rules
  sudo iptables -I INPUT -m set --match-set ghost_whitelist src -j ACCEPT
  sudo iptables -A INPUT -p tcp --dport 22 -j DROP  # Block SSH by default
        """
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=62201,
        help='UDP port to listen on (default: 62201)'
    )
    
    parser.add_argument(
        '-i', '--interface',
        default=None,
        help='Network interface to listen on (default: all)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    # Check capabilities
    check_capabilities()
    
    # Get shared secret from environment
    shared_secret = os.environ.get('GHOST_SECRET_KEY')
    
    if not shared_secret:
        print("ERROR: GHOST_SECRET_KEY environment variable not set", file=sys.stderr)
        print("Run: export GHOST_SECRET_KEY='your_32byte_hex_key'", file=sys.stderr)
        return 1
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Initialize server
        server = GhostServer(shared_secret, verbose=args.verbose)
        
        # Start listening
        server.start(args.port, args.interface)
        
        return 0
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
