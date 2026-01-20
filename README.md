# Saxo Dashboard

Portfolio dashboard that fetches positions from Saxo Bank API.

## Quick Update (when positions change)

```bash
cd saxo-dashboard
python oauth_login_live.py   # Login to get fresh tokens (expires after 1 hour)
python scripts/fetch_positions.py
git add data/holdings.json data/positions.json
git commit -m "Update holdings"
git push
```

**Note:** Yahoo Finance now requires authentication for sector data, so auto-lookup doesn't work anymore. Sectors must be added manually or they show as "Other".

## How Token Encryption Works

Saxo OAuth tokens are sensitive and can't be committed to git directly. Here's the flow:

1. **`oauth_login_live.py`** - Opens browser for Saxo login, saves tokens to `tokens_live.json`
2. **`encrypt_tokens.py`** - Encrypts `tokens_live.json` → `tokens_live.json.enc` using a passphrase
3. **`.tokens_passphrase`** - Local file storing the encryption passphrase (gitignored)
4. **`tokens_live.json.enc`** - Encrypted tokens file (safe to commit)

### GitHub Actions

The workflow decrypts tokens using the `TOKENS_PASSPHRASE` secret. If decryption fails with "InvalidToken" error:

1. Check your local passphrase: `cat .tokens_passphrase`
2. Update GitHub secret: **Settings → Secrets and variables → Actions → TOKENS_PASSPHRASE**
3. Make sure they match exactly

### Re-encrypting tokens

If you need to re-encrypt (e.g., after refreshing tokens):

```bash
python encrypt_tokens.py
git add tokens_live.json.enc
git commit -m "Update encrypted tokens"
git push
```

## GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `TOKENS_PASSPHRASE` | Passphrase to decrypt `tokens_live.json.enc` (from `.tokens_passphrase`) |
| `SAXO_APP_KEY` | Saxo API app key |
| `SAXO_APP_SECRET` | Saxo API app secret |
| `PAT_TOKEN` | GitHub PAT with repo write access (for workflow commits)
