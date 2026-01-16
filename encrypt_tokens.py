"""
Encrypt tokens_live.json for safe storage in git.
Run this after getting new tokens via oauth_login_live.py
Uses Python's cryptography library instead of OpenSSL.
"""
import os
import json
import base64
import secrets
import string

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    print("Installing cryptography library...")
    import subprocess
    subprocess.run(["pip", "install", "cryptography"], check=True)
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def generate_passphrase():
    """Generate a secure random passphrase"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(32))

def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a Fernet key from passphrase"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key

def encrypt_file(input_file: str, output_file: str, passphrase: str):
    """Encrypt a file using Fernet symmetric encryption"""
    # Generate random salt
    salt = secrets.token_bytes(16)

    # Derive key from passphrase
    key = derive_key(passphrase, salt)
    fernet = Fernet(key)

    # Read and encrypt
    with open(input_file, 'rb') as f:
        data = f.read()

    encrypted = fernet.encrypt(data)

    # Save salt + encrypted data
    with open(output_file, 'wb') as f:
        f.write(salt + encrypted)

    return True

def main():
    if not os.path.exists("tokens_live.json"):
        print("Error: tokens_live.json not found. Run oauth_login_live.py first.")
        return

    # Check if passphrase already exists
    passphrase_file = ".tokens_passphrase"
    if os.path.exists(passphrase_file):
        with open(passphrase_file) as f:
            passphrase = f.read().strip()
        print("Using existing passphrase from .tokens_passphrase")
    else:
        passphrase = generate_passphrase()
        with open(passphrase_file, "w") as f:
            f.write(passphrase)
        print(f"Generated new passphrase and saved to {passphrase_file}")

    # Encrypt the tokens
    try:
        encrypt_file("tokens_live.json", "tokens_live.json.enc", passphrase)
        print("Tokens encrypted to tokens_live.json.enc")
        print("\n" + "="*50)
        print("IMPORTANT: Add these secrets to your GitHub repo:")
        print("="*50)
        print(f"\nTOKENS_PASSPHRASE: {passphrase}")
        print(f"SAXO_APP_KEY: a8c97c9fa28f4668aa16b0501b5223bf")
        print(f"SAXO_APP_SECRET: a3c9040b2eeb4a1a98dc45b7a5458fc2")
        print("\nAlso create a PAT_TOKEN with repo write access")
        print("="*50)
    except Exception as e:
        print(f"Error encrypting: {e}")

if __name__ == "__main__":
    main()
