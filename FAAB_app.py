import streamlit as st
import requests
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="FAAB & Waiver Optimizer", layout="wide")

st.title("🏈 Fantasy Football Waiver & FAAB Optimizer")
st.write("Fetch real-time Sleeper trending players, sync your actual league & roster, and receive tailored waiver recommendations.")

# ----------------------------------------------------
# 1. API Helper Functions (Cached)
# ----------------------------------------------------
@st.cache_data(ttl=86400)
def get_all_players():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {}

@st.cache_data(ttl=3600)
def get_trending_adds(hours=24):
    url = f"https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours={hours}&limit=15"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

@st.cache_data(ttl=3600)
def get_trending_drops(hours=24):
    url = f"https://api.sleeper.app/v1/players/nfl/trending/drop?lookback_hours={hours}&limit=15"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

@st.cache_data(ttl=300)
def get_sleeper_user(username):
    url = f"https://api.sleeper.app/v1/user/{username.strip()}"
    response = requests.get(url)
    if response.status_code == 200 and response.json():
        return response.json()
    return None

@st.cache_data(ttl=300)
def get_user_leagues(user_id, season="2026"):
    url = f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/{season}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

@st.cache_data(ttl=300)
def get_league_rosters(league_id):
    url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

@st.cache_data(ttl=300)
def get_league_details(league_id):
    url = f"https://api.sleeper.app/v1/league/{league_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {}

# ----------------------------------------------------
# 2. Sidebar Settings & League Integration
# ----------------------------------------------------
st.sidebar.header("1. Sleeper League Sync")
username_input = st.sidebar.text_input("Sleeper Username", value="", placeholder="e.g., fantasypro123")
season_input = st.sidebar.selectbox("Season", options=["2026", "2025"], index=0)

user_id = None
selected_league = None
my_roster = None
all_rostered_player_ids = set()
my_player_ids = set()
detected_is_faab = False
auto_budget = 100

if username_input:
    user_info = get_sleeper_user(username_input)
    if user_info:
        user_id = user_info.get('user_id')
        st.sidebar.success(f"Connected: {user_info.get('display_name', username_input)}")
        
        leagues = get_user_leagues(user_id, season=season_input)
        if leagues:
            league_options = {l['name']: l for l in leagues}
            selected_league_name = st.sidebar.selectbox("Select Your League", options=list(league_options.keys()))
            selected_league = league_options[selected_league_name]
            
            # Fetch rosters and league details
            rosters = get_league_rosters(selected_league['league_id'])
            league_details = get_league_details(selected_league['league_id'])
            
            # Sleeper waiver_type check:
            # 0 = Rolling / Waiver Priority
            # 1 or 2 = FAAB Bidding / Continuous Waivers
            settings = league_details.get('settings', {})
            waiver_type = settings.get('waiver_type', 0)
            total_budget = settings.get('waiver_budget', 0)
            
            detected_is_faab = (waiver_type in [1, 2]) and (total_budget > 0)
            
            # Extract rostered players
            for r in rosters:
                players_list = r.get('players') or []
                all_rostered_player_ids.update(players_list)
                
                is_owner = (r.get('owner_id') == user_id) or (user_id in (r.get('co_owners') or []))
                if is_owner:
                    my_roster = r
                    my_player_ids = set(players_list)
                    
            if detected_is_faab and my_roster:
                used_budget = my_roster.get('settings', {}).get('waiver_budget_used', 0)
                auto_budget = max(0, total_budget - used_budget)
        else:
            st.sidebar.warning(f"No leagues found for {season_input}.")
    else:
        st.sidebar.error("Username not found.")

st.sidebar.header("2. Waiver Settings")
lookback = st.sidebar.selectbox("Trending Timeframe (Hours)", options=[24, 48, 72], index=0)

# Toggle switch pre-populated by auto-detection
is_faab_league = st.sidebar.toggle(
    "FAAB Bidding Mode ($)", 
    value=detected_is_faab, 
    help="Toggle ON for FAAB dollar bidding, OFF for Waiver Priority claim tiers."
)

if is_faab_league:
    budget = st.sidebar.number_input("Total Remaining FAAB ($)", min_value=1, value=auto_budget, step=5)
else:
    st.sidebar.info("📌 Waiver Priority Mode active (No FAAB). Displaying claim priority tiers.")
    budget = 100

# Load core databases
players_db = get_all_players()
trending_adds = get_trending_adds(hours=lookback)
trending_drops = get_trending_drops(hours=lookback)

# Display User Roster Summary Header
if my_roster and players_db:
    pos_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'K': 0, 'DEF': 0}
    for pid in my_player_ids:
        p = players_db.get(str(pid), {})
        pos = p.get('position')
        if pos in pos_counts:
            pos_counts[pos] += 1
            
    st.subheader("📋 Your Team Roster Breakdown")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Waiver System", "FAAB ($)" if is_faab_league else "Waiver Priority")
    c2.metric("Quarterbacks (QB)", pos_counts['QB'])
    c3.metric("Running Backs (RB)", pos_counts['RB'])
    c4.metric("Wide Receivers (WR)", pos_counts['WR'])
    c5.metric("Tight Ends (TE)", pos_counts['TE'])
    st.markdown("---")

# ----------------------------------------------------
# 3. Main Data Tabs & Recommendation Engine
# ----------------------------------------------------
tab_adds, tab_drops = st.tabs(["📈 Top Trending Adds", "📉 Top Trending Drops"])

# --- TAB 1: TRENDING ADDS ---
with tab_adds:
    if trending_adds and players_db:
        enriched_adds = []
        for item in trending_adds:
            p_id = str(item['player_id'])
            p_info = players_db.get(p_id, {})
            
            full_name = p_info.get('full_name') or f"{p_info.get('first_name', '')} {p_info.get('last_name', '')}".strip()
            if not full_name:
                full_name = f"Player {p_id}"

            position = p_info.get('position', 'N/A')
            team = p_info.get('team') or 'FA'

            if selected_league:
                if p_id in my_player_ids:
                    status = "On Your Roster"
                elif p_id in all_rostered_player_ids:
                    status = "Rostered in League"
                else:
                    status = "Available (Free Agent)"
            else:
                status = "N/A"

            enriched_adds.append({
                'Player': full_name,
                'Position': position,
                'Team': team,
                'Availability': status,
                'Recent Adds': item['count']
            })

        df_adds = pd.DataFrame(enriched_adds)
        df_adds.index = range(1, len(df_adds) + 1)

        position_weights = {'RB': 1.20, 'WR': 1.00, 'TE': 0.80, 'QB': 0.70, 'K': 0.25, 'DEF': 0.25}
        max_adds = df_adds['Recent Adds'].max() if not df_adds.empty else 1
        adds_per_hour = max_adds / lookback
        market_anchor_pct = min(50.0, max(10.0, np.log10(max(adds_per_hour, 10)) * 12.0 - 10.0))

        def calculate_score(row):
            adds = row['Recent Adds']
            pos = row['Position']
            weight = position_weights.get(pos, 1.0)
            relative_share = adds / max_adds
            score = relative_share * market_anchor_pct * weight
            return min(100.0, max(1.0, round(score, 1)))

        df_adds['Target Rating'] = df_adds.apply(calculate_score, axis=1)

        if is_faab_league:
            df_adds['Suggested Bid %'] = df_adds['Target Rating']
            df_adds['Suggested Bid ($)'] = (df_adds['Suggested Bid %'] / 100 * budget).round(0).astype(int)
        else:
            def assign_priority_tier(score):
                if score >= 35.0:
                    return "🔥 Tier 1: Burn Top Priority"
                elif score >= 20.0:
                    return "⚡ Tier 2: High Priority Claim"
                elif score >= 8.0:
                    return "👍 Tier 3: Moderate Claim"
                else:
                    return "👀 Tier 4: Free Agent Stash"

            df_adds['Recommended Claim'] = df_adds['Target Rating'].apply(assign_priority_tier)

        df_chart_adds = df_adds.sort_values(by='Target Rating', ascending=True)
        df_adds['Recent Adds'] = df_adds['Recent Adds'].apply(lambda x: f"{x:,}")

        st.subheader(f"Top Trending Waiver Adds (Past {lookback} Hours)")
        
        if is_faab_league:
            cols_adds = ['Player', 'Position', 'Team', 'Availability', 'Recent Adds', 'Suggested Bid %', 'Suggested Bid ($)']
        else:
            cols_adds = ['Player', 'Position', 'Team', 'Availability', 'Recent Adds', 'Target Rating', 'Recommended Claim']

        if not selected_league:
            cols_adds = [c for c in cols_adds if c != 'Availability']

        st.dataframe(df_adds[cols_adds], use_container_width=True)

        st.subheader("Target Rating Breakdown")
        st.bar_chart(
            df_chart_adds,
            x="Player",
            y="Target Rating",
            sort="-Target Rating"
        )
    else:
        st.warning("Loading trending adds from Sleeper API...")

# --- TAB 2: TRENDING DROPS ---
with tab_drops:
    if trending_drops and players_db:
        enriched_drops = []
        for item in trending_drops:
            p_id = str(item['player_id'])
            p_info = players_db.get(p_id, {})
            
            full_name = p_info.get('full_name') or f"{p_info.get('first_name', '')} {p_info.get('last_name', '')}".strip()
            if not full_name:
                full_name = f"Player {p_id}"

            position = p_info.get('position', 'N/A')
            team = p_info.get('team') or 'FA'

            if selected_league:
                if p_id in my_player_ids:
                    status = "On Your Roster"
                elif p_id in all_rostered_player_ids:
                    status = "Rostered in League"
                else:
                    status = "Available (Free Agent)"
            else:
                status = "N/A"

            enriched_drops.append({
                'Player': full_name,
                'Position': position,
                'Team': team,
                'Availability': status,
                'Recent Drops': item['count']
            })

        df_drops = pd.DataFrame(enriched_drops)
        df_drops.index = range(1, len(df_drops) + 1)

        max_drops = df_drops['Recent Drops'].max() if not df_drops.empty else 1
        
        def calculate_panic_score(row):
            drops = row['Recent Drops']
            relative_share = drops / max_drops
            score = relative_share * 100.0
            return min(100.0, max(1.0, round(score, 1)))

        df_drops['Panic Rating'] = df_drops.apply(calculate_panic_score, axis=1)

        def assign_drop_urgency(score):
            if score >= 60.0:
                return "🚨 Heavy Panic / Cut Candidate"
            elif score >= 30.0:
                return "⚠️ Moderate Churn"
            else:
                return "❄️ Minor Drop Activity"

        df_drops['Market Sentiment'] = df_drops['Panic Rating'].apply(assign_drop_urgency)

        df_chart_drops = df_drops.sort_values(by='Panic Rating', ascending=True)
        df_drops['Recent Drops'] = df_drops['Recent Drops'].apply(lambda x: f"{x:,}")

        st.subheader(f"Top Trending Drops Across Leagues (Past {lookback} Hours)")
        
        cols_drops = ['Player', 'Position', 'Team', 'Availability', 'Recent Drops', 'Panic Rating', 'Market Sentiment']

        if not selected_league:
            cols_drops = [c for c in cols_drops if c != 'Availability']

        st.dataframe(df_drops[cols_drops], use_container_width=True)

        st.subheader("Panic Rating Breakdown")
        st.bar_chart(
            df_chart_drops,
            x="Player",
            y="Panic Rating",
            sort="-Panic Rating"
        )
    else:
        st.warning("Loading trending drops from Sleeper API...")