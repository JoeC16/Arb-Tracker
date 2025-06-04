
import streamlit as st
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

# Full hardcoded league dictionary
SPORTS = {
    # Core Soccer Leagues (wide markets)
    "Premier League": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
    "Champions League": "soccer_uefa_champions_league",
    "Primeira Liga": "soccer_portugal_primeira_liga",
    "Eredivisie": "soccer_netherlands_eredivisie",

    # Obscure Soccer Leagues (h2h only)
    "Super Lig": "soccer_turkey_super_league",
    "Scottish Premiership": "soccer_scotland_premiership",
    "K League": "soccer_south_korea_k_league_1",
    "Liga MX": "soccer_mexico_liga_mex",
    "Chinese Super League": "soccer_china_superleague",
    "Brazil Serie A": "soccer_brazil_campeonato",
    "MLS": "soccer_usa_mls",

    # Tennis (main markets only)
    "ATP Tour": "tennis_atp",
    "WTA Tour": "tennis_wta",
    "Australian Open": "tennis_australian_open",
    "French Open": "tennis_french_open",
    "US Open": "tennis_us_open",
    "Wimbledon": "tennis_wimbledon"
}

# Market logic
WIDE_MARKETS = ["h2h", "draw_no_bet", "double_chance"]
STANDARD_MARKETS = ["h2h"]
BUFFER = 0.015

def fetch_odds(sport_key, markets):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "all",
        "markets": ",".join(markets),
        "oddsFormat": "decimal"
    }
    response = requests.get(url, params=params)
    return response

def find_arbs(matches):
    arbs = []
    for match in matches:
        try:
            bookmakers = match.get("bookmakers", [])
            outcomes = {}
            for book in bookmakers:
                for market in book.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        name = outcome["name"]
                        price = outcome["price"]
                        if name not in outcomes or price > outcomes[name]["price"]:
                            outcomes[name] = {
                                "price": price,
                                "bookmaker": book["title"]
                            }

            if len(outcomes) == 2:
                names = list(outcomes.keys())
                p1 = outcomes[names[0]]["price"]
                p2 = outcomes[names[1]]["price"]
                implied = (1 / p1) + (1 / p2)

                if implied < (1 - BUFFER):
                    profit = round((1 - implied) * 100, 2)
                    arbs.append({
                        "match": match["teams"],
                        "commence_time": match["commence_time"],
                        "market": match["markets"][0]["key"],
                        "bookmakers": outcomes,
                        "profit_margin": profit
                    })
        except:
            continue
    return arbs

st.set_page_config("Global Soccer & Tennis Arb Scanner", layout="wide")
st.title("🌍 Global Arbitrage Scanner")

selected_leagues = st.multiselect("Choose Leagues", options=list(SPORTS.keys()), default=list(SPORTS.keys())[:5])
if st.button("🔍 Run Arbitrage Scan"):
    for league in selected_leagues:
        st.markdown(f"### {league}")
        key = SPORTS[league]
        markets = WIDE_MARKETS if "soccer" in key and any(l in league for l in ["Premier", "Serie", "Liga", "Bundes", "Champions"]) else STANDARD_MARKETS
        response = fetch_odds(key, markets)

        if response.status_code != 200:
            st.warning(f"{league}: API error {response.status_code}")
            continue

        try:
            matches = response.json()
            arbs = find_arbs(matches)
            if not arbs:
                st.info("No arbitrage opportunities found.")
            for arb in arbs:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{arb['match'][0]} vs {arb['match'][1]}** — *{arb['market']}*")
                    st.markdown(f"⏰ {arb['commence_time']}")
                    for team, data in arb["bookmakers"].items():
                        st.markdown(f"- **{team}**: {data['price']} @ {data['bookmaker']}")
                with col2:
                    st.success(f"✅ Profit Margin: **{arb['profit_margin']}%**")
                    stake = st.number_input("Total Stake (£)", value=100.0, key=f"{league}_{arb['commence_time']}")
                    team1, team2 = list(arb["bookmakers"].items())
                    price1 = team1[1]["price"]
                    price2 = team2[1]["price"]
                    stake1 = round(stake * (1 / price1) / ((1 / price1) + (1 / price2)), 2)
                    stake2 = round(stake * (1 / price2) / ((1 / price1) + (1 / price2)), 2)
                    guaranteed = round(min(stake1 * price1, stake2 * price2) - stake, 2)
                    st.markdown(f"🎯 **Stake Guide:**")
                    st.markdown(f"- Bet £{stake1} on **{team1[0]}**")
                    st.markdown(f"- Bet £{stake2} on **{team2[0]}**")
                    st.markdown(f"💰 **Guaranteed Profit:** £{guaranteed}")
        except:
            st.error(f"{league}: failed to parse response.")
