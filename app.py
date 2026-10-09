import streamlit as st
import requests
import pandas as pd

# Page setup
st.set_page_config(page_title="FAAB & Waiver Optimizer", layout="wide")

st.title("🏈 Fantasy Football FAAB & Waiver Optimizer")
st.write("Fetch real-time Sleeper trending players and calculate recommended FAAB bids.")

# Sidebar Controls
st.sidebar.header("User Settings")
budget = st.sidebar.number_input("Total Remaining FAAB ($)", min_value=1, value=100, step=5)
lookback = st.sidebar.selectbox("Trending Timeframe", options=[24, 48, 72], index=0)

# Fetch Trending Adds from Sleeper API
@st.cache_data(ttl=3600)  # Cache results for 1 hour
def get_trending_adds(hours=24):
    url = f"https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours={hours}&limit=15"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

trending = get_trending_adds(hours=lookback)

if trending:
    df = pd.DataFrame(trending)
    
    # Simple bid logic based on add volume
    max_adds = df['count'].max()
    df['Suggested Bid %'] = (df['count'] / max_adds * 20).round(1)  # Max bid ~20% of FAAB
    df['Suggested Bid ($)'] = (df['Suggested Bid %'] / 100 * budget).round(0).astype(int)

    # Format table for UI
    df_display = df.rename(columns={
        'player_id': 'Player ID',
        'count': 'Recent Adds (League-wide)',
    })[['Player ID', 'Recent Adds (League-wide)', 'Suggested Bid %', 'Suggested Bid ($)']]

    st.subheader(f"Top Trending Waiver Adds (Past {lookback} Hours)")
    st.dataframe(df_display, use_container_width=True)

    # Visualizer
    st.subheader("FAAB Allocation Breakdown")
    st.bar_chart(df.set_index('player_id')['Suggested Bid ($)'])

else:
    st.warning("Could not retrieve trending player data. Please try again later.")