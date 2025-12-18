#!/usr/bin/env python3
"""
Ghost Protocol - Shared Secret Key Generator

Generates a cryptographically secure 32-byte shared secret for Ghost Protocol.
This secret must be shared securely between client and server.

Usage:
    python ghost_keygen.py

Security:
    - Uses os.urandom() for cryptographically secure random
    - Output is hex-encoded for easy storage
    - Store in environment variables, NEVER commit to Git
"""
import os
import sys


def generate_shared_secret():
    """
    Generate a cryptographically secure 32-byte shared secret.
    
    Returns:
        str: Hex-encoded 32-byte secret key
    """
    # Generate 32 bytes of cryptographically secure random data
    # This is the key size required by NaCl SecretBox
    secret_bytes = os.urandom(32)
    
    # Encode as hex for easy storage in environment variables
    secret_hex = secret_bytes.hex()
    
    return secret_hex


def main():
    """Main entry point"""
    print("=" * 70)
    print("Ghost Protocol - Shared Secret Generator")
    print("=" * 70)
    print()
    
    # Generate secret
    secret = generate_shared_secret()
    
    print("Generated Shared Secret (32 bytes, hex-encoded):")
    print()
    print(f"  {secret}")
    print()
    print("=" * 70)
    print("SECURITY INSTRUCTIONS:")
    print("=" * 70)
    print()
    print("1. Add this secret to your environment variables:")
    print()
    print("   # On Server:")
    print(f"   export GHOST_SECRET_KEY='{secret}'")
    print("   echo 'export GHOST_SECRET_KEY=\"{secret}\"' >> ~/.bashrc")
    print()
    print("   # On Client:")
    print(f"   export GHOST_SECRET_KEY='{secret}'")
    print("   echo 'export GHOST_SECRET_KEY=\"{secret}\"' >> ~/.bashrc")
    print()
    print("2. NEVER commit this secret to version control!")
    print()
    print("3. Store securely in a password manager if needed")
    print()
    print("4. Rotate this key every 90 days for best security")
    print()
    print("=" * 70)
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
