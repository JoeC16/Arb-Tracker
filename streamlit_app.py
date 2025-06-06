# app.py

import streamlit as st
import requests
import pandas as pd
import time
from itertools import combinations

ODDS_API_KEY = st.secrets["oddsapi_key"]
SUPPORTED_SPORTS = ["tennis", "mma", "darts"]

st.set_page_config(page_title="Arbitrage Scanner", layout="wide")
st.title("💸 Arbitrage Scanner (2-Way Sports)")

refresh_interval = st.sidebar.number_input("⏱ Refresh Interval (minutes)", min_value=1, max_value=60, value=5)
bankroll = st.sidebar.number_input("💰 Bankroll (£)", min_value=10, value=100)
run_button = st.sidebar.button("🔁 Run Scan Now")

def fetch_oddsapi_data():
    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "uk",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    st.error(f"OddsAPI error: {response.status_code}")
    return []

def fake_betfair_lay_odds(event_name, team_name):
    # Placeholder for real Betfair API
    return round(1.8 + 0.1 * (hash(team_name) % 5), 2)

def back_back_arbitrage(bookmakers, event_name, sport):
    opportunities = []

    for (book1, book2) in combinations(bookmakers, 2):
        try:
            market1 = next(m for m in book1["markets"] if m["key"] == "h2h")
            market2 = next(m for m in book2["markets"] if m["key"] == "h2h")
        except StopIteration:
            continue

        o1 = market1["outcomes"]
        o2 = market2["outcomes"]
        if len(o1) != 2 or len(o2) != 2:
            continue

        team1 = o1[0]["name"]
        team2 = o2[1]["name"]
        odds1 = o1[0]["price"]
        odds2 = o2[1]["price"]

        implied_prob = 1 / odds1 + 1 / odds2
        if implied_prob >= 1:
            continue

        stake1 = bankroll * (1 / odds1) / implied_prob
        stake2 = bankroll * (1 / odds2) / implied_prob
        payout1 = stake1 * odds1
        payout2 = stake2 * odds2
        profit = min(payout1, payout2) - bankroll

        opportunities.append({
            "Type": "Back/Back",
            "Sport": sport,
            "Match": event_name,
            "Outcome A": team1,
            "Outcome B": team2,
            "Bookmaker A": book1["title"],
            "Bookmaker B": book2["title"],
            "Odds A": odds1,
            "Odds B": odds2,
            "Stake A": round(stake1, 2),
            "Stake B": round(stake2, 2),
            "Profit (£)": round(profit, 2),
            "ROI (%)": round(profit / bankroll * 100, 2)
        })

    return opportunities

def back_lay_arbitrage(bookmakers, event_name, sport):
    opportunities = []

    for book in bookmakers:
        for market in book["markets"]:
            if market["key"] != "h2h":
                continue

            for outcome in market["outcomes"]:
                team = outcome["name"]
                back_odds = outcome["price"]
                lay_odds = fake_betfair_lay_odds(event_name, team)

                if lay_odds <= 1 or back_odds >= lay_odds:
                    continue

                back_stake = bankroll
                lay_stake = (back_stake * back_odds) / lay_odds
                liability = lay_stake * (lay_odds - 1)
                total_outlay = back_stake + liability
                profit = (back_odds * back_stake - total_outlay)

                if profit > 0:
                    opportunities.append({
                        "Type": "Back/Lay",
                        "Sport": sport,
                        "Match": event_name,
                        "Outcome": team,
                        "Bookmaker": book["title"],
                        "Back Odds": back_odds,
                        "Exchange Lay Odds": lay_odds,
                        "Back Stake": round(back_stake, 2),
                        "Lay Stake": round(lay_stake, 2),
                        "Profit (£)": round(profit, 2),
                        "ROI (%)": round(profit / bankroll * 100, 2)
                    })
    return opportunities

def process_data():
    raw_data = fetch_oddsapi_data()
    backback_rows = []
    backlay_rows = []

    for event in raw_data:
        sport = event.get("sport_key", "")
        if not any(s in sport for s in SUPPORTED_SPORTS):
            continue

        teams = event.get("teams", [])
        if len(teams) != 2:
            continue

        event_name = f"{teams[0]} vs {teams[1]}"
        bookmakers = event.get("bookmakers", [])

        backback_rows.extend(back_back_arbitrage(bookmakers, event_name, sport))
        backlay_rows.extend(back_lay_arbitrage(bookmakers, event_name, sport))

    return pd.DataFrame(backback_rows), pd.DataFrame(backlay_rows)

if run_button or "autorefresh" not in st.session_state:
    st.session_state["autorefresh"] = True

tab1, tab2 = st.tabs(["📊 Back/Back Arbitrage", "📈 Back/Lay Arbitrage"])

with tab1:
    st.write("Scanning for profitable back/back arbitrage...")
    df_backback, _ = process_data()
    if df_backback.empty:
        st.warning("No back/back arbs found.")
    else:
        st.success(f"{len(df_backback)} opportunities found.")
        st.dataframe(df_backback)

with tab2:
    st.write("Scanning for profitable back/lay arbitrage...")
    _, df_backlay = process_data()
    if df_backlay.empty:
        st.warning("No back/lay arbs found.")
    else:
        st.success(f"{len(df_backlay)} opportunities found.")
        st.dataframe(df_backlay)
