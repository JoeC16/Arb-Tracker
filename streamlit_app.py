
import streamlit as st
import requests
from datetime import datetime

API_KEY = st.secrets["API_KEY"]

SPORT_KEYS = {
    "soccer_epl": "⚽ Premier League",
    "soccer_uefa_champs_league": "🏆 Champions League",
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "tennis_atp": "🎾 ATP Tour",
    "tennis_wta": "🎾 WTA Tour"
}

REGIONS = "uk,us,eu,au"
MARKETS = "h2h,spreads,totals,team_totals,draw_no_bet,double_chance,first_half_h2h"

st.set_page_config(page_title="Arbitrage Scanner", layout="wide")
st.title("💸 Arbitrage Scanner — Soccer + Tennis")
st.caption("Live arbitrage detection with stake guide & 2% buffer")

def find_arbs(data, sport_key):
    arbs = []
    for match in data:
        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                outcomes = market.get("outcomes", [])
                if not (2 <= len(outcomes) <= 3):
                    continue
                try:
                    implied_prob = sum(1 / o["price"] for o in outcomes)
                    if implied_prob < 1.02:  # 2% margin buffer
                        arbs.append({
                            "teams": match.get("teams", [o["name"] for o in outcomes]),
                            "market": market.get("key", ""),
                            "bookmaker": bookmaker.get("title", ""),
                            "outcomes": [(o["name"], o["price"]) for o in outcomes],
                            "profit_margin": round((1 - implied_prob) * 100, 2),
                            "sport": sport_key,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                except:
                    continue
    return arbs

if 'arb_history' not in st.session_state:
    st.session_state['arb_history'] = []

if st.button("🔍 Scan for Arbitrage"):
    st.session_state['arb_history'] = []

    for sport_key, sport_label in SPORT_KEYS.items():
        st.subheader(f"🔎 {sport_label}")
        try:
            resp = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={
                    "apiKey": API_KEY,
                    "regions": REGIONS,
                    "markets": MARKETS
                },
                timeout=10
            )
            if resp.status_code == 200:
                matches = resp.json()
                arbs = find_arbs(matches, sport_key)
                st.session_state['arb_history'].extend(arbs)
                st.success(f"✅ Matches: {len(matches)} | Arbs found: {len(arbs)}")
            else:
                st.error(f"{sport_label} API Error: {resp.status_code} - {resp.text}")
        except Exception as e:
            st.error(f"{sport_label} Error: {e}")

if st.session_state['arb_history']:
    st.header("📈 Arbitrage Opportunities")
    for arb in sorted(st.session_state['arb_history'], key=lambda x: x['profit_margin'], reverse=True):
        st.subheader(f"{arb['teams'][0]} vs {arb['teams'][-1]} ({arb['market']})")
        st.caption(f"{arb['sport']} | Bookmaker: {arb['bookmaker']} | {arb['timestamp']}")
        for name, price in arb['outcomes']:
            st.write(f"• {name}: {price}")
        st.success(f"Profit Margin: **{arb['profit_margin']}%**")

        with st.expander("📊 Stake Calculator"):
            total_stake = st.number_input("Total Stake (£)", value=100.0, min_value=1.0, key=arb['timestamp'])
            inv_total = sum(1 / p for _, p in arb['outcomes'])
            bet_allocs = [(name, round((1 / price) / inv_total * total_stake, 2), price)
                          for name, price in arb['outcomes']]
            payout = round(bet_allocs[0][1] * bet_allocs[0][2], 2)
            profit = round(payout - total_stake, 2)

            for name, stake, _ in bet_allocs:
                st.write(f"🔸 Stake £{stake} on {name}")
            st.success(f"💷 Guaranteed Profit: £{profit}")
else:
    st.info("No arbs found yet. Hit scan above.")
