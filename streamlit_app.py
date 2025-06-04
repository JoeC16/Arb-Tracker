
import streamlit as st
import requests
from datetime import datetime

API_KEY = st.secrets["API_KEY"]

REGIONS = "uk,us,eu,au"

# Broader markets for these core soccer leagues
CORE_SOCCER_LEAGUES = {
    "soccer_epl": "Premier League",
    "soccer_uefa_champs_league": "Champions League",
    "soccer_spain_la_liga": "La Liga",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_italy_serie_a": "Serie A",
    "soccer_france_ligue_one": "Ligue 1",
    "soccer_portugal_primeira_liga": "Primeira Liga",
    "soccer_netherlands_eredivisie": "Eredivisie"
}

# Global soccer leagues (standard markets only)
OTHER_SOCCER_LEAGUES = {
    "soccer_brazil_campeonato": "Brazil Serie A",
    "soccer_argentina_primera_division": "Argentina Primera",
    "soccer_usa_mls": "MLS",
    "soccer_turkey_super_lig": "Super Lig",
    "soccer_greece_super_league": "Greek Super League",
    "soccer_denmark_superliga": "Danish Superliga",
    "soccer_scotland_premiership": "Scottish Premiership",
    "soccer_japan_j_league": "J League",
    "soccer_south_korea_kleague": "K League",
    "soccer_australia_aleague": "A-League",
    "soccer_mexico_liga_mx": "Liga MX",
    "soccer_china_super_league": "Chinese Super League"
}

# Tennis leagues (always h2h only)
TENNIS_LEAGUES = {
    "tennis_atp": "ATP Tour",
    "tennis_wta": "WTA Tour",
    "tennis_aus_open": "Australian Open",
    "tennis_us_open": "US Open",
    "tennis_french_open": "French Open",
    "tennis_wimbledon": "Wimbledon"
}

st.set_page_config(page_title="Global Arb Scanner", layout="wide")
st.title("🌍 Arbitrage Scanner — Global Soccer & Tennis")

def fetch_arbs(league_key, label, markets):
    try:
        resp = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{league_key}/odds",
            params={"apiKey": API_KEY, "regions": REGIONS, "markets": markets},
            timeout=10
        )
        if resp.status_code != 200:
            st.warning(f"{label}: API error {resp.status_code}")
            return []
        return find_arbs(resp.json(), league_key, label)
    except Exception as e:
        st.error(f"{label}: Error fetching odds — {e}")
        return []

def find_arbs(matches, sport_key, label):
    arbs = []
    for match in matches:
        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                outcomes = market.get("outcomes", [])
                if not (2 <= len(outcomes) <= 3):
                    continue
                try:
                    implied_prob = sum(1 / o["price"] for o in outcomes)
                    if implied_prob < 1.02:  # 2% profit buffer
                        arbs.append({
                            "teams": match.get("teams", [o["name"] for o in outcomes]),
                            "market": market["key"],
                            "bookmaker": bookmaker["title"],
                            "outcomes": [(o["name"], o["price"]) for o in outcomes],
                            "profit_margin": round((1 - implied_prob) * 100, 2),
                            "sport": label,
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                except:
                    continue
    return arbs

if st.button("🔍 Run Full Scan"):
    st.session_state['arb_history'] = []

    for key, label in CORE_SOCCER_LEAGUES.items():
        arbs = fetch_arbs(key, label, "h2h,draw_no_bet,double_chance")
        st.session_state['arb_history'].extend(arbs)

    for key, label in OTHER_SOCCER_LEAGUES.items():
        arbs = fetch_arbs(key, label, "h2h")
        st.session_state['arb_history'].extend(arbs)

    for key, label in TENNIS_LEAGUES.items():
        arbs = fetch_arbs(key, label, "h2h")
        st.session_state['arb_history'].extend(arbs)

if st.session_state.get('arb_history'):
    st.header("💰 Arbitrage Opportunities Found")
    for arb in sorted(st.session_state['arb_history'], key=lambda x: x['profit_margin'], reverse=True):
        st.subheader(f"{arb['teams'][0]} vs {arb['teams'][-1]} — {arb['market']}")
        st.caption(f"{arb['sport']} | {arb['bookmaker']} | {arb['timestamp']}")
        for name, price in arb['outcomes']:
            st.write(f"• {name}: {price}")
        st.success(f"✅ Profit Margin: **{arb['profit_margin']}%**")

        with st.expander("📊 Stake Calculator"):
            stake = st.number_input("Total Stake (£)", value=100.0, key=arb['timestamp'])
            total_inv = sum(1 / p for _, p in arb['outcomes'])
            split = [(n, round((1 / p) / total_inv * stake, 2), p) for n, p in arb['outcomes']]
            payout = round(split[0][1] * split[0][2], 2)
            profit = round(payout - stake, 2)
            for n, s, _ in split:
                st.write(f"▪️ Stake £{s} on **{n}**")
            st.success(f"💷 Profit: £{profit}")
else:
    st.info("No arbitrage opportunities found. Hit scan to check again.")
