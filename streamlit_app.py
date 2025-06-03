
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("API_KEY")
SPORTS_URL = "https://api.the-odds-api.com/v4/sports"
MARKETS = "h2h,spreads,totals"

def get_all_sport_keys():
    try:
        response = requests.get(SPORTS_URL, params={"apiKey": API_KEY}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {sport['key']: sport['title'] for sport in data if sport.get('active')}
        else:
            return {}
    except Exception:
        return {}

def find_arbs(data, sport_key):
    opportunities = []
    for match in data:
        for bookmaker in match.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if len(market.get('outcomes', [])) == 2:
                    outcome1, outcome2 = market['outcomes']
                    name1, odds1 = outcome1['name'], outcome1['price']
                    name2, odds2 = outcome2['name'], outcome2['price']
                    implied_prob = (1/odds1) + (1/odds2)
                    if implied_prob < 1:
                        profit_margin = (1 - implied_prob) * 100
                        opportunities.append({
                            'match': match.get('teams', [name1, name2]),
                            'team1': (name1, odds1, bookmaker['title']),
                            'team2': (name2, odds2, bookmaker['title']),
                            'market': market.get('key', 'unknown'),
                            'profit_margin': round(profit_margin, 2),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'sport': sport_key
                        })
    return opportunities

st.set_page_config(page_title="Arb Scanner", layout="wide")
st.title("🎯 Arbitrage Scanner with Sport Selector")
st.caption("Now with fallback handling to avoid black screens.")

sports_dict = get_all_sport_keys()

if not sports_dict:
    st.error("⚠️ Could not load active sports list. Please check your API key or try again later.")
    st.stop()

selected_sports = st.multiselect("Select Sports to Scan", options=list(sports_dict.keys()), format_func=lambda x: sports_dict[x])

if 'arb_history' not in st.session_state:
    st.session_state['arb_history'] = []

if st.button("🔍 Run Arbitrage Scan"):
    with st.spinner("Scanning for arbitrage opportunities..."):
        for sport_key in selected_sports:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
                params = {
                    'apiKey': API_KEY,
                    'regions': 'uk',
                    'markets': MARKETS
                }
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    arbs = find_arbs(data, sport_key)
                    st.session_state['arb_history'].extend(arbs)
                else:
                    st.warning(f"{sports_dict[sport_key]}: API Error {response.status_code}")
            except Exception as e:
                st.warning(f"{sports_dict[sport_key]}: Request failed - {e}")

if st.session_state['arb_history']:
    st.header("📋 Arbitrage Opportunities Found")
    for i, arb in enumerate(reversed(st.session_state['arb_history'])):
        st.subheader(f"{arb['match'][0]} vs {arb['match'][1]} ({arb['timestamp']})")
        st.caption(f"Sport: {arb['sport']} — Market: **{arb['market']}**")
        st.write(f"**{arb['team1'][0]}**: {arb['team1'][1]} @ {arb['team1'][2]}")
        st.write(f"**{arb['team2'][0]}**: {arb['team2'][1]} @ {arb['team2'][2]}")
        st.success(f"💰 Arbitrage Profit Margin: **{arb['profit_margin']}%**")

        with st.expander("📊 Stake Calculator"):
            total_stake = st.number_input(f"Total stake for opportunity #{i+1}", min_value=1.0, value=100.0, key=f"stake_{i}")
            odds_a = arb['team1'][1]
            odds_b = arb['team2'][1]
            total_inverse = (1/odds_a) + (1/odds_b)
            stake_a = round((1/odds_a) / total_inverse * total_stake, 2)
            stake_b = round((1/odds_b) / total_inverse * total_stake, 2)
            payout = round(stake_a * odds_a, 2)
            profit = round(payout - total_stake, 2)
            st.write(f"➡️ Stake **£{stake_a}** on {arb['team1'][0]} at {odds_a}")
            st.write(f"➡️ Stake **£{stake_b}** on {arb['team2'][0]} at {odds_b}")
            st.success(f"Guaranteed Payout: £{payout} — Profit: £{profit}")
else:
    st.info("No arbitrage opportunities found yet. Select sports and scan to begin.")
