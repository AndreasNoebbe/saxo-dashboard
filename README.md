lil guide to remember

Given the saxo API only lasts for 1 hour, when new positions are bought/sold, do this:

Also, Yahoo Finance now requires authentication for sector data (they blocked it sometime recently). The auto-lookup doesn't work anymore, hence must be done manually, else flagged as "Other"

```
cd saxo-dashboard
python oauth_login_live.py   # If token expired
python scripts/fetch_positions.py
git add data/holdings.json data/positions.json
git commit -m "Update holdings"
git push

