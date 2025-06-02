
import streamlit as st
import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
API_KEY = os.getenv("API_KEY")
SPORT = 'soccer_epl'
REGIONS = 'uk'
MARKETS = 'h2h'
URL = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds'

SCAN_INTERVAL_MINUTES = 96  # ~15 scans per day

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
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

    return opportunities

st.set_page_config(page_title="Soccer Arb Scanner", layout="wide")
st.title("⚽ Soccer Arbitrage Scanner (UK Bookmakers)")

if 'last_scan' not in st.session_state:
    st.session_state['last_scan'] = datetime.min
if 'arb_history' not in st.session_state:
    st.session_state['arb_history'] = []

now = datetime.now()
if now - st.session_state['last_scan'] >= timedelta(minutes=SCAN_INTERVAL_MINUTES):
    with st.spinner("Scanning for arbitrage opportunities..."):
        params = {
            'apiKey': API_KEY,
            'regions': REGIONS,
            'markets': MARKETS
        }
        resp = requests.get(URL, params=params)

        if resp.status_code == 200:
            matches = resp.json()
            arbs = find_arbs(matches)
            if arbs:
                st.session_state['arb_history'].extend(arbs)
            st.session_state['last_scan'] = now
        else:
            st.error(f"API Error: {resp.status_code} - {resp.text}")

if st.session_state['arb_history']:
    for arb in reversed(st.session_state['arb_history']):
        st.subheader(f"{arb['match'][0]} vs {arb['match'][1]']}  ({arb['timestamp']})")
        st.write(f"**{arb['team1'][0]}**: {arb['team1'][1]} @ {arb['team1'][2]}")
        st.write(f"**{arb['team2'][0]}**: {arb['team2'][1]} @ {arb['team2'][2]}")
        st.success(f"💰 Arbitrage Profit Margin: **{arb['profit_margin']}%**")
else:
    st.info("No arbitrage opportunities found yet. Please wait for next scan.")
