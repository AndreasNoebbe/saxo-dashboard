"""
Encrypt tokens_live.json for safe storage in git.
Run this after getting new tokens via oauth_login_live.py
"""
import subprocess
import os
import secrets
import string

def generate_passphrase():
    """Generate a secure random passphrase"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(32))

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
    result = subprocess.run([
        "openssl", "enc", "-aes-256-cbc", "-pbkdf2",
        "-in", "tokens_live.json",
        "-out", "tokens_live.json.enc",
        "-pass", f"pass:{passphrase}"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print("Tokens encrypted to tokens_live.json.enc")
        print("\n" + "="*50)
        print("IMPORTANT: Add these secrets to your GitHub repo:")
        print("="*50)
        print(f"\nTOKENS_PASSPHRASE: {passphrase}")
        print(f"SAXO_APP_KEY: a8c97c9fa28f4668aa16b0501b5223bf")
        print(f"SAXO_APP_SECRET: a3c9040b2eeb4a1a98dc45b7a5458fc2")
        print("\nAlso create a PAT_TOKEN with repo write access")
        print("="*50)
    else:
        print(f"Error: {result.stderr}")

if __name__ == "__main__":
    main()
