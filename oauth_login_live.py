"""
Saxo OAuth Login Flow - LIVE ENVIRONMENT (HTTPS)
Run this script, it will open a browser for you to login.
After login, it will capture the token and save it.
"""
import webbrowser
import http.server
import ssl
import socketserver
import urllib.parse
import requests
import json
import os
import subprocess
from datetime import datetime, timedelta

# Your LIVE app credentials
APP_KEY = "a8c97c9fa28f4668aa16b0501b5223bf"
APP_SECRET = "a3c9040b2eeb4a1a98dc45b7a5458fc2"
REDIRECT_URI = "https://localhost:8000/callback"

# Saxo OAuth URLs (LIVE)
AUTH_URL = "https://live.logonvalidation.net/authorize"
TOKEN_URL = "https://live.logonvalidation.net/token"

def generate_self_signed_cert():
    """Generate a self-signed certificate for localhost"""
    cert_file = "localhost.pem"
    key_file = "localhost-key.pem"

    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("Using existing SSL certificates")
        return cert_file, key_file

    print("Generating self-signed SSL certificate...")

    # Use OpenSSL to generate certificate
    # First check if openssl is available
    try:
        subprocess.run(["openssl", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("OpenSSL not found. Please install OpenSSL or use the manual method below.")
        print("\nAlternative: Install mkcert (https://github.com/FiloSottile/mkcert)")
        print("  choco install mkcert")
        print("  mkcert -install")
        print("  mkcert localhost")
        return None, None

    # Generate key and certificate
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", key_file, "-out", cert_file,
        "-days", "365", "-nodes",
        "-subj", "/CN=localhost"
    ], capture_output=True)

    print(f"Generated {cert_file} and {key_file}")
    return cert_file, key_file

class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/callback"):
            # Parse the authorization code from the callback
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)

            if "code" in params:
                code = params["code"][0]
                print(f"\n[OK] Got authorization code")

                # Exchange code for tokens
                token_data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": APP_KEY,
                    "client_secret": APP_SECRET,
                }

                response = requests.post(TOKEN_URL, data=token_data)

                print(f"Token response status: {response.status_code}")

                if response.status_code in [200, 201]:
                    tokens = response.json()
                elif response.text and "access_token" in response.text:
                    tokens = json.loads(response.text)
                else:
                    print(f"[ERROR] Token exchange failed: {response.text}")
                    self.send_error(400, "Token exchange failed")
                    return

                # Calculate expiry times
                access_expires = datetime.now() + timedelta(seconds=tokens.get("expires_in", 1200))
                refresh_expires = datetime.now() + timedelta(seconds=tokens.get("refresh_token_expires_in", 3600))

                # Save tokens to file
                token_file = {
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens.get("refresh_token"),
                    "access_token_expires": access_expires.isoformat(),
                    "refresh_token_expires": refresh_expires.isoformat(),
                    "token_type": tokens.get("token_type", "Bearer"),
                    "environment": "live"
                }

                with open("tokens_live.json", "w") as f:
                    json.dump(token_file, f, indent=2)

                print(f"[OK] Access token received (expires: {access_expires})")
                print(f"[OK] Refresh token received (expires: {refresh_expires})")
                print(f"[OK] Tokens saved to tokens_live.json")

                # Send success response to browser
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Success!</h1>
                    <p>Live tokens saved. You can close this window.</p>
                    </body></html>
                """)

                # Signal to stop the server
                self.server.should_stop = True
            else:
                error = params.get("error", ["Unknown"])[0]
                print(f"[ERROR] OAuth error: {error}")
                self.send_error(400, f"OAuth error: {error}")
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # Suppress default logging

def main():
    # Generate SSL certificates
    cert_file, key_file = generate_self_signed_cert()

    if not cert_file:
        print("\nCannot proceed without SSL certificates.")
        return

    # Build authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": APP_KEY,
        "redirect_uri": REDIRECT_URI,
        "state": "portfolio-dashboard-live",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print("=" * 50)
    print("Saxo OAuth Login - LIVE ENVIRONMENT (HTTPS)")
    print("=" * 50)
    print(f"\nOpening browser for login...")
    print(f"If browser doesn't open, visit:\n{auth_url}\n")
    print("NOTE: Your browser may warn about the self-signed certificate.")
    print("      Click 'Advanced' and 'Proceed to localhost' to continue.\n")

    # Start HTTPS server
    with socketserver.TCPServer(("", 8000), OAuthHandler) as httpd:
        # Wrap with SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

        httpd.should_stop = False

        # Open browser
        webbrowser.open(auth_url)

        print("Waiting for login callback on https://localhost:8000/callback ...")

        # Handle requests until we get the token
        while not httpd.should_stop:
            httpd.handle_request()

    print("\nDone! You can now run the dashboard.")

if __name__ == "__main__":
    main()
