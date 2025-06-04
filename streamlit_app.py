
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("API_KEY")
REGIONS = "uk,us,eu,au"

SPORT_MARKETS = {
    "soccer": "h2h,spreads,totals,draw_no_bet,double_chance",
    "basketball_nba": "h2h,spreads,totals",
    "tennis_atp_french_open": "h2h",
    "cricket_t20_blast": "h2h",
    "rugby_union": "h2h"
}

SPORT_KEYS = {
    "soccer": "⚽ Soccer (All)",
    "basketball_nba": "🏀 NBA",
    "tennis_atp_french_open": "🎾 ATP French Open",
    "cricket_t20_blast": "🏏 T20 Blast",
    "rugby_union": "🏉 Rugby Union"
}

st.set_page_config(page_title="Arb Scanner MVP", layout="wide")
st.title("🚀 MVP Arbitrage Scanner")
st.caption("Now using sport-specific market types to avoid 422 errors.")

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
                    if implied_prob < 1.02:
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
                except Exception as e:
                    st.warning(f"Failed to process market: {e}")
    return opportunities

if 'arb_history' not in st.session_state:
    st.session_state['arb_history'] = []

if st.button("🔍 Run Arbitrage Scan"):
    st.session_state['arb_history'] = []
    for sport_key, sport_name in SPORT_KEYS.items():
        try:
            resp = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={
                    "apiKey": API_KEY,
                    "regions": REGIONS,
                    "markets": SPORT_MARKETS[sport_key]
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                st.write(f"{sport_name}: Matches returned: {len(data)}")
                arbs = find_arbs(data, sport_key)
                st.session_state['arb_history'].extend(arbs)
            else:
                st.warning(f"{sport_name}: API Error {resp.status_code} - {resp.text}")
        except Exception as e:
            st.warning(f"{sport_name}: {e}")

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
