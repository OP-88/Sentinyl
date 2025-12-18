#!/usr/bin/env python3
"""
Lazarus Recovery - Setup & Key Generation

Generates the Master Key, splits it into Shamir shards, and creates Tor auth keys.
This is a ONE-TIME setup script. Store the shards securely offline.

Usage:
    python lazarus_setup.py

Security:
    - Master Key is NEVER saved (only its hash)
    - Shards are printed ONCE (write them down!)
    - Use Tor Client Authorization for hidden service access
"""
import os
import sys
import secrets
import hashlib
from pathlib import Path

try:
    from shamirs import shares
except ImportError:
    print("ERROR: shamirs module not installed. Run: pip install shamirs", file=sys.stderr)
    sys.exit(1)

try:
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("ERROR: cryptography module not installed. Run: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class LazarusSetup:
    """Lazarus Recovery setup and key generation"""
    
    # Shamir parameters
    TOTAL_SHARDS = 5
    THRESHOLD = 3
    
    # Master key size
    KEY_SIZE = 32  # 256 bits
    
    def __init__(self):
        """Initialize setup"""
        self.master_key = None
        self.master_hash = None
        self.shards = []
    
    def generate_master_key(self):
        """
        Generate cryptographically secure 32-byte Master Key
        
        Returns:
            bytes: Master key
        """
        # Generate 32 bytes of cryptographically secure random data
        self.master_key = secrets.token_bytes(self.KEY_SIZE)
        
        # Hash the key for verification (SHA-256)
        self.master_hash = hashlib.sha256(self.master_key).hexdigest()
        
        print(f"[*] Generated {self.KEY_SIZE}-byte Master Key")
        print(f"[*] SHA-256 Hash: {self.master_hash}")
        
        return self.master_key
    
    def split_key(self):
        """
        Split Master Key into Shamir shards (3-of-5)
        
        Returns:
            list: Shard hex strings
        """
        # Convert master key to hex string for Shamir library
        master_hex = self.master_key.hex()
        
        # Split into shards (threshold=3, total=5)
        self.shards = shares.split_secret(
            master_hex,
            self.THRESHOLD,
            self.TOTAL_SHARDS
        )
        
        print(f"[*] Split key into {self.TOTAL_SHARDS} shards (threshold: {self.THRESHOLD})")
        
        return self.shards
    
    def save_hash(self, filepath="lazarus.hash"):
        """
        Save Master Key hash to file
        
        Args:
            filepath: Path to save hash
        """
        try:
            with open(filepath, 'w') as f:
                f.write(self.master_hash)
            
            # Secure permissions (owner read-only)
            os.chmod(filepath, 0o400)
            
            print(f"[*] Saved Master Key hash to: {filepath}")
            print(f"[*] File permissions: 400 (read-only)")
            
        except Exception as e:
            print(f"ERROR: Failed to save hash: {e}", file=sys.stderr)
            sys.exit(1)
    
    def generate_tor_keys(self):
        """
        Generate x25519 keypair for Tor Client Authorization
        
        Returns:
            tuple: (private_key_bytes, public_key_bytes)
        """
        # Generate x25519 private key
        private_key = x25519.X25519PrivateKey.generate()
        
        # Derive public key
        public_key = private_key.public_key()
        
        # Serialize keys to bytes
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return private_bytes, public_bytes
    
    def print_shards(self):
        """Print shards in a user-friendly format"""
        print("\n" + "=" * 70)
        print("LAZARUS RECOVERY - MASTER KEY SHARDS")
        print("=" * 70)
        print()
        print("⚠️  CRITICAL SECURITY INSTRUCTIONS:")
        print()
        print("1. Write down these shards ON PAPER (never digital)")
        print("2. Store each shard in a SEPARATE SECURE LOCATION")
        print("3. ANY 3 SHARDS can recover the system")
        print("4. These shards will NEVER be shown again!")
        print()
        print("=" * 70)
        print()
        
        for i, shard in enumerate(self.shards, 1):
            print(f"SHARD #{i}:")
            print(f"  {shard}")
            print()
        
        print("=" * 70)
        print()
    
    def print_tor_instructions(self, private_key, public_key):
        """
        Print Tor Hidden Service setup instructions
        
        Args:
            private_key: x25519 private key bytes
            public_key: x25519 public key bytes
        """
        # Encode keys in base32 (Tor format)
        import base64
        
        # Tor uses base32 encoding for keys
        private_b32 = base64.b32encode(private_key).decode('ascii').strip('=')
        public_b32 = base64.b32encode(public_key).decode('ascii').strip('=')
        
        print("\n" + "=" * 70)
        print("TOR HIDDEN SERVICE CONFIGURATION")
        print("=" * 70)
        print()
        print("Step 1: Configure Tor Hidden Service")
        print("---------------------------------------")
        print()
        print("Edit /etc/tor/torrc and add:")
        print()
        print("  HiddenServiceDir /var/lib/tor/lazarus/")
        print("  HiddenServicePort 80 127.0.0.1:9999")
        print("  HiddenServiceVersion 3")
        print()
        print("Step 2: Create Client Authorization (Server Side)")
        print("---------------------------------------------------")
        print()
        print("Create file: /var/lib/tor/lazarus/authorized_clients/admin.auth")
        print()
        print(f"Content:")
        print(f"  descriptor:x25519:{public_b32}")
        print()
        print("Step 3: Client Authorization Key (Admin Side)")
        print("-----------------------------------------------")
        print()
        print("Save this private key to your admin machine:")
        print()
        print(f"File: ~/.tor/authorized_clients/lazarus.auth_private")
        print(f"Content:")
        print(f"  {private_b32}")
        print()
        print("Step 4: Restart Tor")
        print("--------------------")
        print()
        print("  sudo systemctl restart tor")
        print()
        print("Step 5: Get Your Onion Address")
        print("--------------------------------")
        print()
        print("  sudo cat /var/lib/tor/lazarus/hostname")
        print()
        print("=" * 70)
        print()


def main():
    """Main entry point"""
    print("=" * 70)
    print("Lazarus Recovery - Setup & Key Generation")
    print("=" * 70)
    print()
    
    setup = LazarusSetup()
    
    # Step 1: Generate Master Key
    print("[1/5] Generating Master Key...")
    setup.generate_master_key()
    print()
    
    # Step 2: Split into shards
    print("[2/5] Splitting key into Shamir shards...")
    setup.split_key()
    print()
    
    # Step 3: Save hash
    print("[3/5] Saving Master Key hash...")
    setup.save_hash()
    print()
    
    # Step 4: Generate Tor keys
    print("[4/5] Generating Tor Client Authorization keys...")
    private_key, public_key = setup.generate_tor_keys()
    print("[*] Generated x25519 keypair for Tor")
    print()
    
    # Step 5: Print everything
    print("[5/5] Displaying shards and instructions...")
    print()
    
    # Print shards (user must write these down!)
    setup.print_shards()
    
    # Print Tor setup instructions
    setup.print_tor_instructions(private_key, public_key)
    
    print()
    print("=" * 70)
    print("✓ SETUP COMPLETE")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("  1. Write down all 5 shards securely")
    print("  2. Configure Tor Hidden Service (see instructions above)")
    print("  3. Start lazarus_server.py")
    print("  4. Access via Tor Browser with client authorization")
    print()
    print("⚠️  SECURITY WARNING:")
    print("  - The Master Key is NOT saved anywhere (only its hash)")
    print("  - Shards are your ONLY way to recover")
    print("  - Losing 3+ shards = permanent lockout")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
