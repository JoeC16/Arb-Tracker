
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("API_KEY")
SPORTS_URL = "https://api.the-odds-api.com/v4/sports"
REGIONS = "uk,us,eu,au"
MARKET_POOL = ["h2h", "spreads", "totals", "team_totals"]

def get_all_sport_keys():
    try:
        response = requests.get(SPORTS_URL, params={"apiKey": API_KEY}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {sport['key']: sport['title'] for sport in data if sport.get('active')}
        else:
            return {}
    except:
        return {}

def get_supported_markets(sport_key):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/markets"
        response = requests.get(url, params={"apiKey": API_KEY}, timeout=10)
        if response.status_code == 200:
            return [m['key'] for m in response.json()]
        return []
    except:
        return []

def find_arbs(data, sport_key):
    opportunities = []
    for match in data:
        for bookmaker in match.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if 'lay' in market['key'].lower():
                    continue
                outcomes = market.get('outcomes', [])
                if not (2 <= len(outcomes) <= 3):
                    continue
                try:
                    implied_prob = sum(1 / o['price'] for o in outcomes)
                    if implied_prob < 1:
                        profit = (1 - implied_prob) * 100
                        match_teams = match.get('teams', [o['name'] for o in outcomes])
                        opportunities.append({
                            'match': match_teams,
                            'outcomes': [(o['name'], o['price']) for o in outcomes],
                            'bookmaker': bookmaker['title'],
                            'market': market['key'],
                            'profit_margin': round(profit, 2),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'sport': sport_key
                        })
                except:
                    continue
    return opportunities

st.set_page_config(page_title="Multi-Outcome Arb Scanner", layout="wide")
st.title("📊 Arbitrage Scanner — 2 & 3 Outcome Support")
st.caption("Now includes 3-way markets (e.g. Win/Draw/Win). Scans all bookmakers and calculates optimal stakes.")

sports_dict = get_all_sport_keys()
if not sports_dict:
    st.error("⚠️ Could not load sports list.")
    st.stop()

all_keys = list(sports_dict.keys())
selected_sports = st.multiselect("Choose sports", all_keys, format_func=lambda x: sports_dict[x])
if st.button("Select All"):
    selected_sports = all_keys

if 'arb_history' not in st.session_state:
    st.session_state['arb_history'] = []

if st.button("🔍 Run Arbitrage Scan"):
    st.session_state['arb_history'] = []
    for sport_key in selected_sports:
        supported = get_supported_markets(sport_key)
        valid_markets = [m for m in MARKET_POOL if m in supported]
        if not valid_markets:
            st.warning(f"{sports_dict[sport_key]}: No supported markets found.")
            continue
        try:
            resp = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={
                    "apiKey": API_KEY,
                    "regions": REGIONS,
                    "markets": ",".join(valid_markets)
                },
                timeout=10
            )
            if resp.status_code == 200:
                arbs = find_arbs(resp.json(), sport_key)
                st.session_state['arb_history'].extend(arbs)
            else:
                st.warning(f"{sports_dict[sport_key]}: API Error {resp.status_code}")
        except Exception as e:
            st.warning(f"{sports_dict[sport_key]}: {e}")

if st.session_state['arb_history']:
    st.header("✅ Sorted Arbitrage Opportunities")
    sorted_arbs = sorted(st.session_state['arb_history'], key=lambda x: x['profit_margin'], reverse=True)
    for i, arb in enumerate(sorted_arbs):
        st.subheader(f"{arb['match'][0]} vs {arb['match'][-1]} ({arb['timestamp']})")
        st.caption(f"Market: {arb['market']} | Sport: {arb['sport']} | Bookmaker: {arb['bookmaker']}")
        for name, odds in arb['outcomes']:
            st.write(f"{name}: {odds}")
        st.success(f"Profit Margin: {arb['profit_margin']}%")

        with st.expander("💰 Stake Calculator"):
            stake = st.number_input(f"Total Stake #{i+1}", value=100.0, min_value=1.0, key=f"stake_{i}")
            inv = sum(1 / o[1] for o in arb['outcomes'])
            splits = [(o[0], round((1 / o[1]) / inv * stake, 2), o[1]) for o in arb['outcomes']]
            payout = round(splits[0][1] * splits[0][2], 2)
            profit = round(payout - stake, 2)
            for name, amount, _ in splits:
                st.write(f"Bet £{amount} on {name}")
            st.success(f"Guaranteed Profit: £{profit}")
else:
    st.info("No arbitrage opportunities found.")
