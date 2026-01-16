"""
Decrypt tokens_live.json.enc for use in GitHub Actions.
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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

def decrypt_file(input_file: str, output_file: str, passphrase: str):
    """Decrypt a file using Fernet symmetric encryption"""
    with open(input_file, 'rb') as f:
        data = f.read()

    # Extract salt (first 16 bytes) and encrypted data
    salt = data[:16]
    encrypted = data[16:]

    # Derive key from passphrase
    key = derive_key(passphrase, salt)
    fernet = Fernet(key)

    # Decrypt
    decrypted = fernet.decrypt(encrypted)

    with open(output_file, 'wb') as f:
        f.write(decrypted)

    return True

if __name__ == "__main__":
    passphrase = os.environ.get("TOKENS_PASSPHRASE")
    if not passphrase:
        print("Error: TOKENS_PASSPHRASE environment variable not set")
        exit(1)

    decrypt_file("tokens_live.json.enc", "tokens_live.json", passphrase)
    print("Tokens decrypted successfully")
