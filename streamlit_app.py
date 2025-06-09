import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import difflib

st.set_page_config(page_title="Arbitrage Betting Scanner", layout="wide")
st.title("🎯 Arbitrage Betting Scanner")

# Secure API key from Streamlit secrets
ODDS_API_KEY = st.secrets["ODDS_API_KEY"]

# -------------------------------
# Fetch Available Sports Dynamically
# -------------------------------
@st.cache_data(ttl=3600)
def get_available_sports():
    url = "https://api.the-odds-api.com/v4/sports/"
    resp = requests.get(url, params={"apiKey": ODDS_API_KEY})
    if resp.status_code != 200:
        st.error("Could not fetch sports list from OddsAPI.")
        return []
    return resp.json()

sports_list = get_available_sports()
sports_map = {s["title"]: s["key"] for s in sports_list if s.get("active")}
sports_options = list(sports_map.keys())
default_selection = sports_options[:3] if len(sports_options) >= 3 else sports_options

selected_titles = st.sidebar.multiselect(
    "Choose Sports to Scan",
    options=sports_options,
    default=default_selection
)
sports_filter = [sports_map[title] for title in selected_titles]

# -------------------------------
# User Config
# -------------------------------
bankroll = st.sidebar.number_input("Bankroll (£)", value=100.0)
min_profit = st.sidebar.slider("Minimum Profit %", 0.1, 5.0, 1.0)
refresh = st.sidebar.slider("Auto-refresh (sec)", 30, 300, 60)

# -------------------------------
# API Helpers
# -------------------------------

@st.cache_data(ttl=300)
def get_oddsapi_data(sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "uk,eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    resp = requests.get(url, params=params)
    return resp.json() if resp.status_code == 200 else []

def get_smarkets_event_ids():
    url = "https://api.smarkets.com/v3/popular_event_ids/"
    return requests.get(url).json().get("popular_event_ids", [])

def get_smarkets_event(event_id):
    url = f"https://api.smarkets.com/v3/events/{event_id}/"
    return requests.get(url).json()

def get_smarkets_quotes(market_id):
    url = f"https://api.smarkets.com/v3/markets/{market_id}/quotes/"
    return requests.get(url).json()

# -------------------------------
# Utility Logic
# -------------------------------

def match_event_name(name, candidates):
    return difflib.get_close_matches(name, candidates, n=1, cutoff=0.6)

def is_arbitrage(back, lay):
    if back <= 1.01 or lay <= 1.01:
        return False, 0
    margin = (1 / back) + (1 / lay)
    return margin < 1, round((1 - margin) * 100, 2)

# -------------------------------
# Main Arbitrage Logic
# -------------------------------

arbs = []
for sport in sports_filter:
    oddsapi_events = get_oddsapi_data(sport)
    smarket_event_ids = get_smarkets_event_ids()
    
    # Build map of Smarkets lay prices
    smarkets = {}
    for eid in smarket_event_ids:
        ed = get_smarkets_event(eid)
        if "event" not in ed:
            continue
        name = ed["event"]["name"]
        for mid in ed["event"].get("markets", []):
            quotes = get_smarkets_quotes(mid)
            for cid, c in quotes.get("contracts", {}).items():
                smarkets[f"{name}|{cid}"] = {
                    "lay": c.get("lay_price", 0),
                    "back": c.get("back_price", 0),
                    "market_id": mid
                }

    # Scan for arbitrage
    for ev in oddsapi_events:
        all_teams = " vs ".join(ev.get("teams", []))
        kickoff = ev.get("commence_time", "")[:19]
        for book in ev.get("bookmakers", []):
            for market in book.get("markets", []):
                for outcome in market.get("outcomes", []):
                    back_team = outcome["name"]
                    back_odds = outcome["price"]
                    key = match_event_name(back_team, list(smarkets.keys()))
                    if not key:
                        continue
                    smarket_data = smarkets.get(key[0])
                    if not smarket_data:
                        continue
                    lay_odds = smarket_data["lay"]
                    valid, profit_pct = is_arbitrage(back_odds, lay_odds)
                    if valid and profit_pct >= min_profit:
                        est_profit = bankroll * (profit_pct / 100)
                        arbs.append({
                            "Teams": all_teams,
                            "Bookmaker": book["title"],
                            "Back": f"{back_team} @ {back_odds}",
                            "Lay": f"{back_team} @ {lay_odds}",
                            "Profit %": profit_pct,
                            "Est. Profit (£)": round(est_profit, 2),
                            "Kickoff": kickoff
                        })

# -------------------------------
# Display
# -------------------------------

df = pd.DataFrame(arbs)
if not df.empty:
    st.success(f"Found {len(df)} arbitrage opportunities.")
    st.dataframe(df.sort_values("Profit %", ascending=False))
else:
    st.warning("No arbitrage opportunities found.")
    st.caption("Try selecting different sports or adjusting filters.")
