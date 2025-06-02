
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("API_KEY")

SPORTS = {
    "soccer": "⚽ Soccer (All Leagues)",
    "tennis": "🎾 Tennis",
    "mma": "🥊 MMA/UFC",
    "basketball_nba": "🏀 Basketball (NBA)",
    "americanfootball_nfl": "🏈 American Football (NFL)"
}

URL_TEMPLATE = "https://api.the-odds-api.com/v4/sports/{}/odds"

def find_arbs(data):
    opportunities = []
    for match in data:
        outcomes = match.get('bookmakers', [])
        best_odds = {}

        for bookmaker in outcomes:
            market = bookmaker.get('markets', [])[0] if bookmaker.get('markets') else {}
            for outcome in market.get('outcomes', []):
                name = outcome['name']
                price = outcome['price']
                if name not in best_odds or price > best_odds[name]['price']:
                    best_odds[name] = {
                        'price': price,
                        'bookmaker': bookmaker['title']
                    }

        if len(best_odds) == 2:
            team1, team2 = list(best_odds.keys())
            odds1 = best_odds[team1]['price']
            odds2 = best_odds[team2]['price']
            implied_prob = (1/odds1) + (1/odds2)
            if implied_prob < 1:
                profit_margin = (1 - implied_prob) * 100
                opportunities.append({
                    'match': match['teams'],
                    'team1': (team1, odds1, best_odds[team1]['bookmaker']),
                    'team2': (team2, odds2, best_odds[team2]['bookmaker']),
                    'profit_margin': round(profit_margin, 2),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'sport': match.get('sport_key', 'unknown')
                })

    return opportunities

st.set_page_config(page_title="Multi-Sport Arb Scanner", layout="wide")
st.title("🎯 Arbitrage Scanner — 5 Sports")
st.caption("Scans for 2-outcome arbitrage from top UK bookmakers across multiple sports.")

if 'arb_history' not in st.session_state:
    st.session_state['arb_history'] = []

if st.button("🔍 Run Arbitrage Scan Now"):
    with st.spinner("Scanning all sports..."):
        for sport_key in SPORTS.keys():
            url = URL_TEMPLATE.format(sport_key)
            params = {
                'apiKey': API_KEY,
                'regions': 'uk',
                'markets': 'h2h'
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                arbs = find_arbs(data)
                st.session_state['arb_history'].extend(arbs)
            else:
                st.error(f"{SPORTS[sport_key]} API Error: {response.status_code}")

if st.session_state['arb_history']:
    st.header("📋 Arbitrage Opportunities Found")
    for arb in reversed(st.session_state['arb_history']):
        st.subheader(f"{arb['match'][0]} vs {arb['match'][1]} ({arb['timestamp']})")
        st.caption(f"Sport: {arb['sport']}")
        st.write(f"**{arb['team1'][0]}**: {arb['team1'][1]} @ {arb['team1'][2]}")
        st.write(f"**{arb['team2'][0]}**: {arb['team2'][1]} @ {arb['team2'][2]}")
        st.success(f"💰 Arbitrage Profit Margin: **{arb['profit_margin']}%**")
else:
    st.info("No arbitrage opportunities found yet. Click the scan button above to run.")
