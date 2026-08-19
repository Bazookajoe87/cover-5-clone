import streamlit as st
import requests
import psycopg2
from datetime import datetime
import json

# 1. Connect to your free Neon/Supabase database
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# Initialize Database Tables if they don't exist
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spreads (
            game_id TEXT PRIMARY KEY,
            spread_value NUMERIC(3,1) DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS user_picks (
            username TEXT,
            week INT,
            game_id TEXT,
            selected_team TEXT,
            PRIMARY KEY (username, week, game_id)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    st.error(f"Database connection error: {e}")

st.set_page_config(page_title="Cover 5 Replica", page_icon="🏈")
st.title("🏈 Free Cover 5 League")

# Sidebar - User Login & Admin Command
username = st.sidebar.text_input("Enter Your Name:", value="Player1").strip().lower()
is_admin = st.sidebar.checkbox("I am the Admin/Boss")
current_week = st.sidebar.selectbox("Select NFL Week", list(range(1, 19)), index=0)

# 2. Fetch Live NFL Schedule and Scores from free ESPN feed
@st.cache_data(ttl=300) 
def get_espn_data(week):
    # Added seasontype=2 to force ESPN to fetch Regular Season schedule records
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}"
    res = requests.get(url).json()
    games_list = []
    
    if 'events' in res:
        for event in res['events']:
            comp = event['competitions'][0]
            status = event['status']['type']['state'] 
            kickoff_str = event['date'] 
            
            competitors = comp['competitors']
            home_team = ""
            away_team = ""
            home_score = 0
            away_score = 0
            
            for team_data in competitors:
                team_name = team_data['team']['abbreviation']
                raw_score = team_data.get('score', 0)
                score_val = int(raw_score) if raw_score else 0
                
                if team_data['homeAway'] == 'home':
                    home_team = team_name
                    home_score = score_val
                else:
                    away_team = team_name
                    away_score = score_val
            
            games_list.append({
                "id": event['id'], "home": home_team, "away": away_team,
                "home_score": home_score, "away_score": away_score,
                "status": status, "kickoff": kickoff_str
            })
    return games_list

games = []
try:
    games = get_espn_data(current_week)
except Exception as e:
    st.error("Waiting for live sports data feed to connect... Try refreshing.")

# Fetch spreads entered by the admin from DB
db_spreads = {}
my_saved_picks = {}

try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT game_id, spread_value FROM spreads")
    db_spreads = dict(cur.fetchall())

    # Fetch what this current user has already picked this week
    cur.execute("SELECT game_id, selected_team FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
    my_saved_picks = dict(cur.fetchall())
    cur.close()
    conn.close()
except Exception:
    pass

# 3. ADMIN COMMAND SCREEN (For entering spreads)
if is_admin:
    st.subheader("🛠️ Admin Command: Set Point Spreads")
    st.caption("Enter the point spreads for the home teams (e.g., -7 for favorite, 3 for underdog)")
    if games:
        conn = get_db_connection()
        cur = conn.cursor()
        for g in games:
            current_val = float(db_spreads.get(g['id'], 0.0))
            new_spread = st.number_input(f"{g['away']} @ {g['home']}", value=current_val, step=0.5, key=f"spread_{g['id']}")
            if new_spread != current_val:
                cur.execute("INSERT INTO spreads (game_id, spread_value) VALUES (%s, %s) ON CONFLICT (game_id) DO UPDATE SET spread_value = EXCLUDED.spread_value", (g['id'], new_spread))
                conn.commit()
                st.rerun()
        cur.close()
        conn.close()

# 4. USER INTERFACE: THE MATCHUPS BOARD
st.subheader(f"Week {current_week} Matchup Board")
total_picks_made = len(my_saved_picks)

if games:
    conn = get_db_connection()
    cur = conn.cursor()
    for g in games:
        spread = float(db_spreads.get(g['id'], 0.0))
        display_line = f"{g['home']} -{abs(spread)}" if spread >= 0 else f"{g['home']} +{abs(spread)}"
        
        st.write(f"🏈 **{g['away']} @ {g['home']}** (Line: {display_line})")
        st.caption(f"Status: {g['status'].upper()} | Score: {g['away']} {g['away_score']} - {g['home_score']} {g['home']}")
        
        # KICKOFF LOCK LOGIC: Lock picks if game has started
        game_started = g['status'] != 'pre'
        disabled_for_user = game_started or (total_picks_made >= 5 and g['id'] not in my_saved_picks)
        
        col1, col2 = st.columns(2)
        with col1:
            is_picked = my_saved_picks.get(g['id']) == "HOME"
            if st.button(f"Pick {g['home']}", key=f"btn_h_{g['id']}", disabled=disabled_for_user, type="primary" if is_picked else "secondary"):
                if is_picked:
                    cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                else:
                    cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'HOME') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                conn.commit()
                st.rerun()
                
        with col2:
            is_picked = my_saved_picks.get(g['id']) == "AWAY"
            if st.button(f"Pick {g['away']}", key=f"btn_a_{g['id']}", disabled=disabled_for_user, type="primary" if is_picked else "secondary"):
                if is_picked:
                    cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                else:
                    cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'AWAY') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                conn.commit()
                st.rerun()
        st.divider()
    cur.close()
    conn.close()
else:
    st.info("No games scheduled for this week or data loading.")

# 5. LIVE INDIVIDUAL DASHBOARD & SCORE COMPUTATION
st.subheader(f"📊 Your Week {current_week} Tracker ({total_picks_made}/5 Picks)")
my_week_score = 0.0

if games:
    for g_id, choice in my_saved_picks.items():
        try:
            g = next(item for item in games if item["id"] == g_id)
            spread = float(db_spreads.get(g_id, 0.0))
            
            actual_margin = g['home_score'] - g['away_score']
            home_cover_points = actual_margin - spread
            
            game_points = home_cover_points if choice == "HOME" else -home_cover_points
            my_week_score += game_points
            
            st.write(f"🔹 {g['away']} @ {g['home']} | Selected: {choice} | Live Points: **{game_points:+.1f}**")
        except StopIteration:
            pass

st.metric(label="Your Total Weekly Points", value=f"{my_week_score:+.1f}")

# 6. LEADERBOARD SYSTEM (Season Long Standings)
st.subheader("🏆 Multi-Week Season Standings")
try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, week, game_id, selected_team FROM user_picks")
    all_historical_picks = cur.fetchall()
    cur.close()
    conn.close()

    standings = {}
    for p_user, p_week, p_gid, p_choice in all_historical_picks:
        if p_user not in standings:
            standings[p_user] = 0.0
            
        try:
            hist_games = get_espn_data(p_week)
            g = next(item for item in hist_games if item["id"] == p_gid)
            s_val = float(db_spreads.get(p_gid, 0.0))
            margin = g['home_score'] - g['away_score']
            pts = (margin - s_val) if p_choice == "HOME" else -(margin - s_val)
            standings[p_user] += pts
        except Exception:
            pass

    sorted_standings = sorted(standings.items(), key=lambda x: x, reverse=True)
    for rank, (player, score) in enumerate(sorted_standings, 1):
        st.write(f"{rank}. 👤 **{player.upper()}** — Total Score: `{score:+.1f}`")
except Exception:
    pass
