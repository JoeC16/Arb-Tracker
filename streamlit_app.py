
import streamlit as st
import requests
from datetime import datetime

API_KEY = st.secrets["API_KEY"]

# Define core leagues for expanded market scan
CORE_SOCCER_LEAGUES = {
    "soccer_epl": "🇬🇧 Premier League",
    "soccer_uefa_champs_league": "🏆 Champions League",
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_italy_serie_a": "🇮🇹 Serie A"
}

# Other soccer leagues (h2h only)
OTHER_SOCCER_LEAGUES = {
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_portugal_primeira_liga": "🇵🇹 Primeira Liga",
    "soccer_france_ligue_one": "🇫🇷 Ligue 1",
    "soccer_usa_mls": "🇺🇸 MLS"
}

# Tennis leagues (always h2h only)
TENNIS_LEAGUES = {
    "tennis_atp": "🎾 ATP Tour",
    "tennis_wta": "🎾 WTA Tour",
    "tennis_aus_open": "🎾 Australian Open",
    "tennis_us_open": "🎾 US Open",
    "tennis_french_open": "🎾 French Open",
    "tennis_wimbledon": "🎾 Wimbledon"
}

REGIONS = "uk,us,eu,au"

st.set_page_config(page_title="Arbitrage Scanner", layout="wide")
st.title("💸 Arbitrage Scanner — Soccer & Tennis (Per-League)")
st.caption("Scans individual leagues with tailored market logic and a 2% profit buffer.")

def get_arbs_for_league(league_key, label, markets):
    try:
        response = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{league_key}/odds",
            params={
                "apiKey": API_KEY,
                "regions": REGIONS,
                "markets": markets
            },
            timeout=10
        )
        if response.status_code != 200:
            st.warning(f"{label}: API Error {response.status_code}")
            return []
        matches = response.json()
        return find_arbs(matches, league_key, label)
    except Exception as e:
        st.error(f"{label}: Error fetching data — {e}")
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
                    if implied_prob < 1.02:  # Profit buffer
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

if st.button("🔍 Scan Now"):
    st.session_state['arb_history'] = []

    # Core Soccer: Wider markets
    for key, label in CORE_SOCCER_LEAGUES.items():
        st.subheader(f"⚽ {label}")
        arbs = get_arbs_for_league(key, label, "h2h,draw_no_bet,double_chance")
        st.session_state['arb_history'].extend(arbs)

    # Other Soccer: h2h only
    for key, label in OTHER_SOCCER_LEAGUES.items():
        st.subheader(f"⚽ {label}")
        arbs = get_arbs_for_league(key, label, "h2h")
        st.session_state['arb_history'].extend(arbs)

    # Tennis: h2h only
    for key, label in TENNIS_LEAGUES.items():
        st.subheader(f"{label}")
        arbs = get_arbs_for_league(key, label, "h2h")
        st.session_state['arb_history'].extend(arbs)

if st.session_state.get('arb_history'):
    st.header("📈 Arbitrage Opportunities")
    for arb in sorted(st.session_state['arb_history'], key=lambda x: x['profit_margin'], reverse=True):
        st.subheader(f"{arb['teams'][0]} vs {arb['teams'][-1]} — {arb['market']}")
        st.caption(f"{arb['sport']} | Bookmaker: {arb['bookmaker']} | {arb['timestamp']}")
        for name, price in arb['outcomes']:
            st.write(f"• {name}: {price}")
        st.success(f"Profit Margin: **{arb['profit_margin']}%**")

        with st.expander("📊 Stake Calculator"):
            total_stake = st.number_input("Total Stake (£)", value=100.0, min_value=1.0, key=arb['timestamp'])
            inv_total = sum(1 / p for _, p in arb['outcomes'])
            bet_allocs = [(name, round((1 / price) / inv_total * total_stake, 2), price)
                          for name, price in arb['outcomes']]
            payout = round(bet_allocs[0][1] * bet_allocs[0][2], 2)
            profit = round(payout - total_stake, 2)

            for name, stake, _ in bet_allocs:
                st.write(f"🔸 Stake £{stake} on {name}")
            st.success(f"💷 Guaranteed Profit: £{profit}")
else:
    st.info("No arbitrage found yet. Run a scan to begin.")
