import streamlit as st
import requests
import pandas as pd

# Page Configuration
st.set_page_config(page_title="FAAB & Waiver Optimizer", layout="wide")

st.title("🏈 Fantasy Football FAAB & Waiver Optimizer")
st.write("Fetch real-time Sleeper trending players, map actual player details, and calculate FAAB recommendations.")

# Sidebar Settings
st.sidebar.header("User Settings")
budget = st.sidebar.number_input("Total Remaining FAAB ($)", min_value=1, value=100, step=5)
lookback = st.sidebar.selectbox("Trending Timeframe (Hours)", options=[24, 48, 72], index=0)

# 1. Fetch All NFL Players (Cached for 24 hours to optimize performance)
@st.cache_data(ttl=86400)
def get_all_players():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {}

# 2. Fetch Trending Adds from Sleeper
@st.cache_data(ttl=3600)
def get_trending_adds(hours=24):
    url = f"https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours={hours}&limit=15"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

# Load player database and trending list
players_db = get_all_players()
trending = get_trending_adds(hours=lookback)

if trending and players_db:
    # 3. Map Player IDs to Names, Positions, and Teams
    enriched_list = []
    for item in trending:
        p_id = str(item['player_id'])
        p_info = players_db.get(p_id, {})
        
        full_name = p_info.get('full_name') or f"{p_info.get('first_name', '')} {p_info.get('last_name', '')}".strip()
        if not full_name:
            full_name = f"Player {p_id}"

        position = p_info.get('position', 'N/A')
        team = p_info.get('team') or 'FA'

        enriched_list.append({
            'Player': full_name,
            'Position': position,
            'Team': team,
            'Recent Adds': item['count']
        })

    df = pd.DataFrame(enriched_list)

    # 4. Set 1-based indexing for display (1 to 15 instead of 0 to 14)
    df.index = range(1, len(df) + 1)

    # 5. Calculate FAAB Recommendation Logic
    max_adds = df['Recent Adds'].max() if not df.empty else 1
    df['Suggested Bid %'] = (df['Recent Adds'] / max_adds * 20).round(1)  # Max ~20% of budget
    df['Suggested Bid ($)'] = (df['Suggested Bid %'] / 100 * budget).round(0).astype(int)

    # 6. Prepare Chart DataFrame (Before formatting 'Recent Adds' to string)
    df_chart = df.sort_values(by='Suggested Bid ($)', ascending=True)

    # 7. Format 'Recent Adds' column with comma separators for clean table display
    df['Recent Adds'] = df['Recent Adds'].apply(lambda x: f"{x:,}")

    # Display Table
    st.subheader(f"Top Trending Waiver Adds (Past {lookback} Hours)")
    st.dataframe(
        df[['Player', 'Position', 'Team', 'Recent Adds', 'Suggested Bid %', 'Suggested Bid ($)']],
        use_container_width=True
    )

    # Display Chart
    st.subheader("FAAB Allocation Breakdown ($)")
    st.bar_chart(
        df_chart,
        x="Player",
        y="Suggested Bid ($)",
        sort="-Suggested Bid ($)"
    )

else:
    st.warning("Loading data from Sleeper API... If this takes a moment, please refresh.")