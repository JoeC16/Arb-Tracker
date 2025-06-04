
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
SPORT = 'soccer_epl'
REGIONS = 'uk'
MARKETS = 'h2h,spreads,totals,draw_no_bet,double_chance'
URL = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds'

def find_arbs(data):
    opportunities = []
    for match in data:
        outcomes = match.get('bookmakers', [])
        best_odds = {}

        for bookmaker in outcomes:
            for market in bookmaker.get('markets', []):
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
                    'profit_margin': round(profit_margin, 2)
                })

    return opportunities

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
        for arb in arbs:
            print(f"\nMATCH: {arb['match'][0]} vs {arb['match'][1]}")
            print(f"{arb['team1'][0]}: {arb['team1'][1]} @ {arb['team1'][2]}")
            print(f"{arb['team2'][0]}: {arb['team2'][1]} @ {arb['team2'][2]}")
            print(f"→ Arbitrage Profit Margin: {arb['profit_margin']}%")
    else:
        print("No arbitrage opportunities found.")
else:
    print(f"Error: {resp.status_code}, {resp.text}")
