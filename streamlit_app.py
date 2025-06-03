
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
        response = requests.get(SPORTS_URL, params={"apiKey": API_KEY}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {sport['key']: sport['title'] for sport in data if sport.get('active')}
        else:
            return {}
    except:
        return {}

def find_arbs(data, sport_key):
    opportunities = []
    for match in data:
        for bookmaker in match.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if len(market.get('outcomes', [])) == 2:
                    o1, o2 = market['outcomes']
                    name1, odds1 = o1['name'], o1['price']
                    name2, odds2 = o2['name'], o2['price']
                    implied_prob = (1/odds1) + (1/odds2)
                    if implied_prob < 1:
                        profit = (1 - implied_prob) * 100
                        opportunities.append({
                            'match': match.get('teams', [name1, name2]),
                            'team1': (name1, odds1, bookmaker['title']),
                            'team2': (name2, odds2, bookmaker['title']),
                            'market': market['key'],
                            'profit_margin': round(profit, 2),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'sport': sport_key
                        })
    return opportunities

st.set_page_config(page_title="Arb Tracker", layout="wide")
st.title("🎯 All-Sport Arbitrage Scanner")
st.caption("Scan head-to-head, spread, and total markets across all OddsAPI sports.")

sports_dict = get_all_sport_keys()

if not sports_dict:
    st.error("⚠️ Could not load active sports. Check API key or connection.")
    st.stop()

selected_sports = st.multiselect("Select sports to scan", options=list(sports_dict.keys()), format_func=lambda x: sports_dict[x])

if 'arb_history' not in st.session_state:
    st.session_state['arb_history'] = []

if st.button("🔍 Scan Now"):
    for sport_key in selected_sports:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {"apiKey": API_KEY, "regions": "uk", "markets": MARKETS}
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                arbs = find_arbs(data, sport_key)
                st.session_state['arb_history'].extend(arbs)
            else:
                st.warning(f"{sports_dict[sport_key]}: API Error {response.status_code}")
        except Exception as e:
            st.warning(f"{sports_dict[sport_key]}: {e}")

if st.session_state['arb_history']:
    st.header("💸 Arbitrage Opportunities")
    for i, arb in enumerate(reversed(st.session_state['arb_history'])):
        st.subheader(f"{arb['match'][0]} vs {arb['match'][1]} ({arb['timestamp']})")
        st.caption(f"Market: {arb['market']} | Sport: {arb['sport']}")
        st.write(f"**{arb['team1'][0]}**: {arb['team1'][1]} @ {arb['team1'][2]}")
        st.write(f"**{arb['team2'][0]}**: {arb['team2'][1]} @ {arb['team2'][2]}")
        st.success(f"Profit Margin: **{arb['profit_margin']}%**")

        with st.expander("📊 Stake Calculator"):
            stake = st.number_input(f"Total Stake (£) #{i+1}", value=100.0, min_value=1.0, key=f"stake_{i}")
            o1, o2 = arb['team1'][1], arb['team2'][1]
            inv = (1/o1) + (1/o2)
            s1 = round((1/o1)/inv * stake, 2)
            s2 = round((1/o2)/inv * stake, 2)
            payout = round(s1 * o1, 2)
            profit = round(payout - stake, 2)
            st.write(f"Bet £{s1} on {arb['team1'][0]}")
            st.write(f"Bet £{s2} on {arb['team2'][0]}")
            st.success(f"Guaranteed Profit: £{profit}")
else:
    st.info("No arbs yet. Select sports and scan.")
