
# streamlit_app.py

import streamlit as st
import requests
import pandas as pd

ODDS_API_KEY = "e5cdfb14833bd219712d7ec1ce0b09b3"
BASE_URL = "https://api.the-odds-api.com/v4"
REGION = "uk"
TOTAL_STAKE = 100
MIN_PROFIT_MARGIN = 0.02

@st.cache_data(show_spinner=False)
def fetch_sports():
    url = f"{BASE_URL}/sports/?apiKey={ODDS_API_KEY}"
    r = requests.get(url)
    if r.status_code != 200:
        st.error(f"Failed to fetch sports: {r.status_code} - {r.text}")
        return []
    return r.json()

@st.cache_data(show_spinner=False)
def fetch_odds(sport_key):
    url = f"{BASE_URL}/sports/{sport_key}/odds/"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': REGION,
        'oddsFormat': 'decimal'
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return []
    return r.json()

def calculate_implied_probabilities(odds):
    return [1 / o for o in odds if o > 0]

def detect_arbitrage(event):
    if not isinstance(event, dict):
        return []

    if not event.get("home_team") or not event.get("away_team"):
        return []

    arbitrages = []

    for bookmaker in event.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            outcomes = market.get('outcomes', [])
            if len(outcomes) not in [2, 3]:
                continue

            # Build a dictionary of the best odds per outcome
            best_odds = {}
            for outcome in outcomes:
                name = outcome['name']
                price = outcome['price']
                if name not in best_odds or price > best_odds[name]['price']:
                    best_odds[name] = {'price': price, 'bookmaker': bookmaker['title']}

            # Safety: require full coverage for 2-way or 3-way market
            if len(best_odds) != len(set(best_odds.keys())):
                continue  # avoid duplicates

            if len(best_odds) not in [2, 3]:
                continue  # incomplete coverage

            odds = [o['price'] for o in best_odds.values()]
            implied = calculate_implied_probabilities(odds)
            total_implied = sum(implied)

            if total_implied >= 1.0:
                continue  # no arb on implied probs

            # Stake distribution
            stakes = [(1/o)/total_implied * TOTAL_STAKE for o in odds]

            # Simulate payout for each outcome
            returns = [s * o for s, o in zip(stakes, odds)]
            min_return = min(returns)

            # 🔒 Enforce real arbitrage only
            if min_return < TOTAL_STAKE:
                continue  # fake arb or uncovered outcome

            profit = min_return - TOTAL_STAKE
            roi = profit / TOTAL_STAKE * 100

            arbitrages.append({
                'sport': event.get('sport_title', 'N/A'),
                'event': f"{event.get('home_team', '')} vs {event.get('away_team', '')}",
                'market': market['key'],
                'bookmakers': [o['bookmaker'] for o in best_odds.values()],
                'odds': odds,
                'outcomes': list(best_odds.keys()),
                'outcome_type': f"{len(best_odds)}-way",
                'total_implied_prob': round(total_implied, 4),
                'profit_margin_%': round((1 - total_implied) * 100, 2),
                'stake_distribution': [round(s, 2) for s in stakes],
                'guaranteed_profit_£': round(profit, 2),
                'ROI_%': round(roi, 2)
            })

    return arbitrages

# UI
st.set_page_config(page_title="UK Bookie Arbitrage Scanner", layout="wide")
st.title("💸 UK Bookmaker Arbitrage Finder (Full Book Mode)")
st.caption("Using a £100 fixed stake — scanning ALL markets from ALL UK bookmakers.")

stake = st.number_input("Total Stake (£)", min_value=10, max_value=1000, value=TOTAL_STAKE)
sports = fetch_sports()
sport_titles = [s['title'] for s in sports if 'title' in s and 'key' in s]
sport_map = {s['title']: s['key'] for s in sports if 'title' in s and 'key' in s}

st.info(f"Full book mode active — scanning {len(sport_titles)} sports.")

if st.button("🔍 Run Full Bookie Sweep"):
    all_arbs = []
    progress = st.progress(0)
    status = st.empty()

    for i, sport_title in enumerate(sport_titles):
        sport_key = sport_map[sport_title]
        status.text(f"Fetching odds for: {sport_title}")
        odds_data = fetch_odds(sport_key)
        for event in odds_data:
            arbs = detect_arbitrage(event)
            all_arbs.extend(arbs)
        progress.progress((i + 1) / len(sport_titles))

    progress.empty()
    status.empty()

    if not all_arbs:
        st.warning("No arbitrage opportunities found at this time.")
    else:
        df = pd.DataFrame(all_arbs)
        df_sorted = df.sort_values("profit_margin_%", ascending=False)

        st.success(f"✅ Found {len(df_sorted)} arbitrage opportunities!\n")

        for index, row in df_sorted.iterrows():
            st.subheader(f"🏟 {row['event']} — {row['market']}")
            st.markdown(f"**Sport:** {row['sport']}")
            st.markdown(f"**Profit Margin:** `{row['profit_margin_%']}%` &nbsp;&nbsp;|&nbsp;&nbsp; **ROI:** `{row['ROI_%']}%`")
            st.markdown(f"**Implied Probability Total:** `{row['total_implied_prob']}`")
            st.write("### 💡 Bet Breakdown (Based on £100 Stake):")

            for i in range(len(row['bookmakers'])):
                bm = row['bookmakers'][i]
                odds = row['odds'][i]
                stake_amt = row['stake_distribution'][i]
                outcome = row['outcomes'][i]
                st.markdown(f"✅ Bet **£{stake_amt:.2f}** on '**{outcome}**' @ **{odds}** with **{bm}**")

            st.markdown(f"💰 **Guaranteed Return:** £{TOTAL_STAKE + row['guaranteed_profit_£']:.2f}")
            st.markdown(f"📈 **Guaranteed Profit:** £{row['guaranteed_profit_£']:.2f}")
            st.markdown("---")

        st.download_button("💾 Download CSV", df_sorted.to_csv(index=False), file_name="arbitrage_opportunities.csv")
