"""
Fetch portfolio positions from Saxo OpenAPI and save to JSON for the dashboard.
"""
import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TOKENS_FILE = PROJECT_DIR / "tokens_live.json"
DATA_DIR = PROJECT_DIR / "data"
POSITIONS_FILE = DATA_DIR / "positions.json"

# Saxo API
BASE_URL = "https://gateway.saxobank.com/openapi"
TOKEN_URL = "https://live.logonvalidation.net/token"

# App credentials (for token refresh)
APP_KEY = os.environ.get("SAXO_APP_KEY", "a8c97c9fa28f4668aa16b0501b5223bf")
APP_SECRET = os.environ.get("SAXO_APP_SECRET", "a3c9040b2eeb4a1a98dc45b7a5458fc2")

# Sector mapping for stocks
SECTOR_MAP = {
    "NOVOb:xcse": "Healthcare",
    "NVO:xnys": "Healthcare",
    "MSTR:xnas": "Technology",
    "JD:xnas": "Consumer Cyclical",
    "PYPL:xnas": "Financial Services",
    "XPEV:xnys": "Consumer Cyclical",
    "DUOL:xnas": "Technology",
    "FISV:xnas": "Financial Services",
}

def load_tokens():
    """Load tokens from file"""
    if not TOKENS_FILE.exists():
        raise FileNotFoundError(f"Tokens file not found: {TOKENS_FILE}")

    with open(TOKENS_FILE) as f:
        return json.load(f)

def save_tokens(tokens):
    """Save tokens to file"""
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def refresh_access_token(refresh_token):
    """Use refresh token to get a new access token"""
    print("Refreshing access token...")

    response = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": APP_KEY,
        "client_secret": APP_SECRET,
    })

    if response.status_code != 200 and "access_token" not in response.text:
        raise Exception(f"Token refresh failed: {response.text}")

    data = response.json()

    access_expires = datetime.now() + timedelta(seconds=data.get("expires_in", 1200))
    refresh_expires = datetime.now() + timedelta(seconds=data.get("refresh_token_expires_in", 3600))

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "access_token_expires": access_expires.isoformat(),
        "refresh_token_expires": refresh_expires.isoformat(),
        "token_type": "Bearer",
        "environment": "live"
    }

def get_valid_token():
    """Get a valid access token, refreshing if necessary"""
    tokens = load_tokens()

    expires = datetime.fromisoformat(tokens["access_token_expires"])
    if datetime.now() > expires - timedelta(minutes=2):
        print("Access token expired or expiring soon")
        tokens = refresh_access_token(tokens["refresh_token"])
        save_tokens(tokens)
        print("Token refreshed successfully")

    return tokens["access_token"]

def fetch_balances(access_token):
    """Fetch account balances from Saxo - includes market values even when markets closed"""
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(f"{BASE_URL}/port/v1/balances/me", headers=headers)
    response.raise_for_status()

    return response.json()

def fetch_net_positions(access_token):
    """Fetch net positions (aggregated)"""
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(f"{BASE_URL}/port/v1/netpositions/me", headers=headers)
    response.raise_for_status()

    return response.json()

def fetch_instrument_details(access_token, uics):
    """Fetch instrument details for given UICs"""
    headers = {"Authorization": f"Bearer {access_token}"}

    all_instruments = {}
    uic_list = list(set(uics))

    for i in range(0, len(uic_list), 25):
        batch = uic_list[i:i+25]
        uic_param = ",".join(str(u) for u in batch)

        response = requests.get(
            f"{BASE_URL}/ref/v1/instruments/details",
            headers=headers,
            params={"Uics": uic_param, "AssetTypes": "Stock"}
        )

        if response.status_code == 200:
            data = response.json()
            for inst in data.get("Data", []):
                all_instruments[inst["Uic"]] = inst

    return all_instruments

def build_positions(net_positions, balances, instruments):
    """Build positions list using data from multiple sources"""

    # Extract market values from balances (available even when markets closed)
    market_values_by_symbol = {}
    collateral_details = balances.get("MarginCollateralNotAvailableDetail", {})
    for item in collateral_details.get("InstrumentCollateralDetails", []):
        symbol = item.get("Symbol", "")
        market_values_by_symbol[symbol] = item.get("MarketValue", 0)

    positions = []

    for pos in net_positions.get("Data", []):
        base = pos.get("NetPositionBase", {})
        view = pos.get("NetPositionView", {})
        uic = base.get("Uic")

        instrument = instruments.get(uic, {})
        symbol = instrument.get("Symbol", f"UIC:{uic}")

        # Get market value from balances (more reliable when markets closed)
        market_value_dkk = market_values_by_symbol.get(symbol, 0)

        # Calculate market value in original currency
        conversion_rate = view.get("ConversionRateCurrent", 1)
        if conversion_rate > 0:
            market_value = market_value_dkk / conversion_rate
        else:
            market_value = 0

        amount = base.get("Amount", 0)
        avg_price = view.get("AverageOpenPrice", 0)
        current_price = view.get("CurrentPrice", 0)

        # If current price is 0 (markets closed), calculate from market value
        if current_price == 0 and amount > 0 and market_value > 0:
            current_price = market_value / amount

        positions.append({
            "uic": uic,
            "symbol": symbol,
            "description": instrument.get("Description", view.get("Description", "Unknown")),
            "currency": instrument.get("CurrencyCode", view.get("ExposureCurrency", "USD")),
            "amount": amount,
            "avg_price": round(avg_price, 2),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "market_value_dkk": round(market_value_dkk, 2),
            "profit_loss": round(view.get("ProfitLossOnTrade", 0), 2),
            "profit_loss_dkk": round(view.get("ProfitLossOnTradeInBaseCurrency", 0), 2),
            "profit_loss_pct": round((current_price - avg_price) / avg_price * 100, 2) if avg_price > 0 else 0,
            "sector": SECTOR_MAP.get(symbol, "Other"),
            "asset_type": base.get("AssetType", "Stock"),
            "market_state": base.get("MarketState", "Unknown"),
        })

    # Sort by market value descending
    positions.sort(key=lambda x: x["market_value_dkk"], reverse=True)

    return positions

def calculate_allocations(positions, total_value):
    """Calculate allocation percentages"""
    # By holding
    holdings_allocation = []
    for pos in positions:
        pct = (pos["market_value_dkk"] / total_value * 100) if total_value > 0 else 0
        holdings_allocation.append({
            "symbol": pos["symbol"],
            "description": pos["description"],
            "value": pos["market_value_dkk"],
            "percentage": round(pct, 2)
        })

    holdings_allocation.sort(key=lambda x: x["value"], reverse=True)

    # By sector
    sector_totals = {}
    for pos in positions:
        sector = pos["sector"]
        if sector not in sector_totals:
            sector_totals[sector] = 0
        sector_totals[sector] += pos["market_value_dkk"]

    sector_allocation = []
    for sector, value in sector_totals.items():
        pct = (value / total_value * 100) if total_value > 0 else 0
        sector_allocation.append({
            "sector": sector,
            "value": round(value, 2),
            "percentage": round(pct, 2)
        })

    sector_allocation.sort(key=lambda x: x["value"], reverse=True)

    return holdings_allocation, sector_allocation

def main():
    print(f"Fetching Saxo portfolio at {datetime.now().isoformat()}")

    DATA_DIR.mkdir(exist_ok=True)

    access_token = get_valid_token()

    # Fetch all data
    balances = fetch_balances(access_token)
    net_positions = fetch_net_positions(access_token)

    # Get UICs for instrument details
    uics = [pos["NetPositionBase"]["Uic"] for pos in net_positions.get("Data", [])]
    instruments = fetch_instrument_details(access_token, uics)

    # Build positions
    positions = build_positions(net_positions, balances, instruments)

    # Get totals
    total_value = balances.get("TotalValue", 0)
    cash_balance = balances.get("CashBalance", 0)
    positions_value = balances.get("UnrealizedPositionsValue", 0)

    # Use extended hours data if available (more accurate when markets closed)
    extended = balances.get("ExtendedTradingHoursData", {})
    if extended:
        positions_value = extended.get("UnrealizedPositionsValue", positions_value)
        total_value = extended.get("TotalValue", total_value)

    # Calculate allocations
    holdings_allocation, sector_allocation = calculate_allocations(positions, positions_value)

    # Build output
    output = {
        "last_updated": datetime.now().isoformat(),
        "currency": balances.get("Currency", "DKK"),
        "summary": {
            "total_value": round(total_value, 2),
            "cash_balance": round(cash_balance, 2),
            "positions_value": round(positions_value, 2),
            "open_positions_count": balances.get("OpenPositionsCount", 0),
            "net_positions_count": balances.get("NetPositionsCount", 0),
        },
        "positions": positions,
        "allocations": {
            "by_holding": holdings_allocation,
            "by_sector": sector_allocation,
        }
    }

    with open(POSITIONS_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(positions)} positions to {POSITIONS_FILE}")
    print(f"Total portfolio value: {total_value:,.2f} {output['currency']}")

if __name__ == "__main__":
    main()
