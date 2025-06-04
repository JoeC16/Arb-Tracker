
# app.py

import streamlit as st
import requests
import pandas as pd

ODDS_API_KEY = "YOUR_API_KEY_HERE"
BASE_URL = "https://api.the-odds-api.com/v4"
REGION = "uk"
MARKET_TYPES = ['h2h', 'totals', 'spreads', 'draw_no_bet', 'double_chance']
TOTAL_STAKE = 100
MIN_PROFIT_MARGIN = 0.02

@st.cache_data(show_spinner=False)
def fetch_sports():
    url = f"{BASE_URL}/sports/?apiKey={ODDS_API_KEY}"
    return requests.get(url).json()

@st.cache_data(show_spinner=False)
def fetch_odds(sport_key):
    url = f"{BASE_URL}/sports/{sport_key}/odds/"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': REGION,
        'markets': ",".join(MARKET_TYPES),
        'oddsFormat': 'decimal'
    }
    return requests.get(url, params=params).json()

def calculate_implied_probabilities(odds):
    return [1 / o for o in odds if o > 0]

def detect_arbitrage(event):
    arbitrages = []
    for bookmaker in event.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            outcomes = market.get('outcomes', [])
            if len(outcomes) not in [2, 3]:
                continue

            best_odds = {}
            for outcome in outcomes:
                name = outcome['name']
                price = outcome['price']
                if name not in best_odds or price > best_odds[name]['price']:
                    best_odds[name] = {'price': price, 'bookmaker': bookmaker['title']}

            if len(best_odds) in [2, 3]:
                odds = [o['price'] for o in best_odds.values()]
                implied = calculate_implied_probabilities(odds)
                total_implied = sum(implied)
                if total_implied < 1.0:
                    margin = (1 - total_implied) * 100
                    if margin < MIN_PROFIT_MARGIN * 100:
                        continue
                    stakes = [(1/o)/total_implied * TOTAL_STAKE for o in odds]
                    profit = min([s * o for s, o in zip(stakes, odds)]) - TOTAL_STAKE
                    roi = profit / TOTAL_STAKE * 100
                    arbitrages.append({
                        'sport': event['sport_title'],
                        'event': f"{event['home_team']} vs {event.get('away_team', '')}",
                        'market': market['key'],
                        'bookmakers': list(best_odds.values()),
                        'odds': odds,
                        'total_implied_prob': round(total_implied, 4),
                        'profit_margin_%': round(margin, 2),
                        'stake_distribution': [round(s, 2) for s in stakes],
                        'guaranteed_profit_£': round(profit, 2),
                        'ROI_%': round(roi, 2)
                    })
    return arbitrages

# UI
st.title("🎯 UK Bookmakers Arbitrage Finder")
stake = st.number_input("Total Stake (£)", min_value=10, max_value=1000, value=TOTAL_STAKE)
sports = fetch_sports()
selected_sports = st.multiselect("Select Sports to Scan", options=[s['title'] for s in sports], default=[])

if st.button("Scan for Arbitrage Opportunities"):
    all_arbs = []
    sport_map = {s['title']: s['key'] for s in sports}
    for sport_title in selected_sports:
        odds_data = fetch_odds(sport_map[sport_title])
        for event in odds_data:
            arbs = detect_arbitrage(event)
            all_arbs.extend(arbs)

    if not all_arbs:
        st.warning("No arbitrage opportunities found at this time.")
    else:
        df = pd.DataFrame(all_arbs)
        df_sorted = df.sort_values("profit_margin_%", ascending=False)
        st.dataframe(df_sorted)
        st.download_button("Download CSV", df_sorted.to_csv(index=False), file_name="arbitrage_opportunities.csv")
