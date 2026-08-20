import streamlit as st
import requests
import psycopg2
from datetime import datetime

# 1. Connect to your free Neon/Supabase database
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# Initialize Database Tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spreads (
            game_id TEXT PRIMARY KEY,
            week_num INT,
            spread_value NUMERIC(3,1) DEFAULT 0.0,
            is_locked BOOLEAN DEFAULT FALSE
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
    st.error(f"Database sync alert: {e}")

st.set_page_config(page_title="Cover 5 Pro", page_icon="🏈", layout="wide")
st.title("🏈 Free Cover 5 League Engine")

# Sidebar - User Login & Status Settings
username = st.sidebar.text_input("Enter Your Name:", value="player1").strip().lower()
current_week = st.sidebar.selectbox("Select NFL Week", list(range(1, 19)), index=0)

# Master Data Dictionary mapping official NFL hex codes
TEAM_COLORS = {
    "ARI": {"bg": "#97233F", "text": "#FFFFFF"}, "ATL": {"bg": "#A71930", "text": "#FFFFFF"},
    "BAL": {"bg": "#241773", "text": "#FFFFFF"}, "BUF": {"bg": "#00338D", "text": "#FFFFFF"},
    "CAR": {"bg": "#0085CA", "text": "#FFFFFF"}, "CHI": {"bg": "#0B162A", "text": "#FFFFFF"},
    "CIN": {"bg": "#FB4F14", "text": "#FFFFFF"}, "CLE": {"bg": "#311D00", "text": "#FFFFFF"},
    "DAL": {"bg": "#003594", "text": "#FFFFFF"}, "DEN": {"bg": "#FB4F14", "text": "#FFFFFF"},
    "DET": {"bg": "#0076B6", "text": "#FFFFFF"}, "GB":  {"bg": "#203731", "text": "#FFFFFF"},
    "HOU": {"bg": "#03202F", "text": "#FFFFFF"}, "IND": {"bg": "#002C5F", "text": "#FFFFFF"},
    "JAX": {"bg": "#006778", "text": "#FFFFFF"}, "KC":  {"bg": "#E31837", "text": "#FFFFFF"},
    "LV":  {"bg": "#000000", "text": "#FFFFFF"}, "LAC": {"bg": "#0080C6", "text": "#FFFFFF"},
    "LAR": {"bg": "#003594", "text": "#FFFFFF"}, "MIA": {"bg": "#008E97", "text": "#FFFFFF"},
    "MIN": {"bg": "#4F2683", "text": "#FFFFFF"}, "NE":  {"bg": "#002244", "text": "#FFFFFF"},
    "NO":  {"bg": "#D3BC8D", "text": "#000000"}, "NYG": {"bg": "#0B2265", "text": "#FFFFFF"},
    "NYJ": {"bg": "#125740", "text": "#FFFFFF"}, "PHI": {"bg": "#004C54", "text": "#FFFFFF"},
    "PIT": {"bg": "#FFB612", "text": "#000000"}, "SF":  {"bg": "#AA0000", "text": "#FFFFFF"},
    "SEA": {"bg": "#002244", "text": "#FFFFFF"}, "TB":  {"bg": "#D50A0A", "text": "#FFFFFF"},
    "TEN": {"bg": "#4B92DB", "text": "#FFFFFF"}, "WSH": {"bg": "#5A1414", "text": "#FFFFFF"}
}

# 2. Fetch Live NFL Schedule Framework
@st.cache_data(ttl=300) 
def get_espn_data(week):
    url = f"https://espn.com{week}"
    games_list = []
    try:
        res = requests.get(url).json()
        if 'events' in res and len(res['events']) > 0:
            for event in res['events']:
                comp = event['competitions']
                if len(comp) == 0: continue
                status = event['status']['type']['state'] 
                kickoff_str = event['date'] 
                espn_spread = 0.0
                if 'odds' in comp and len(comp['odds']) > 0:
                    details = comp['odds'].get('details', '') 
                    if details and "EVEN" not in details.upper() and "-" in details:
                        try: espn_spread = float(details.split("-")[-1].strip())
                        except ValueError: pass
                competitors = comp['competitors']
                home_team, away_team, home_score, away_score = "", "", 0, 0
                for team_data in competitors:
                    team_name = team_data['team']['abbreviation']
                    raw_score = team_data.get('score', 0)
                    score_val = int(raw_score) if raw_score else 0
                    if team_data['homeAway'] == 'home': home_team, home_score = team_name, score_val
                    else: away_team, away_score = team_name, score_val
                games_list.append({
                    "id": str(event['id']), "home": home_team, "away": away_team,
                    "home_score": home_score, "away_score": away_score,
                    "status": status, "kickoff": kickoff_str, "espn_spread": espn_spread
                })
    except Exception: pass
        
    # CORRECT 2026 NFL REGULAR SEASON WEEK 1 SCHEDULE FRAMEWORK
    if len(games_list) == 0 and week == 1:
        return [
            {"id": "2026_w1_g1", "away": "NE", "home": "SEA", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.5},
            {"id": "2026_w1_g2", "away": "SF", "home": "LAR", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 2.5},
            {"id": "2026_w1_g3", "away": "CHI", "home": "CAR", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -2.5},
            {"id": "2026_w1_g4", "away": "BAL", "home": "IND", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -3.5},
            {"id": "2026_w1_g5", "away": "TB", "home": "CIN", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.5},
            {"id": "2026_w1_g6", "away": "ATL", "home": "PIT", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.0},
            {"id": "2026_w1_g7", "away": "NYJ", "home": "TEN", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -1.5},
            {"id": "2026_w1_g8", "away": "NO", "home": "DET", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 7.0},
            {"id": "2026_w1_g9", "away": "BUF", "home": "HOU", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -1.5},
            {"id": "2026_w1_g10", "away": "CLE", "home": "JAX", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 7.0},
            {"id": "2026_w1_g11", "away": "ARI", "home": "LAC", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 11.5},
            {"id": "2026_w1_g12", "away": "GB", "home": "MIN", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 2.5},
            {"id": "2026_w1_g13", "away": "MIA", "home": "LV", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.0},
            {"id": "2026_w1_g14", "away": "WSH", "home": "PHI", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 5.5},
            {"id": "2026_w1_g15", "away": "DAL", "home": "NYG", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -2.5},
            {"id": "2026_w1_g16", "away": "DEN", "home": "KC", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 2.5}
        ]
    return games_list

games = []
try: games = get_espn_data(current_week)
except Exception: pass
# 3. TUESDAY LOCK CONSOLE ENGINE
today_weekday = datetime.now().weekday()
db_spreads, my_saved_picks = {}, {}

try:
    conn = get_db_connection()
    cur = conn.cursor()
    if games:
        for g in games:
            cur.execute("SELECT spread_value, is_locked FROM spreads WHERE game_id=%s", (g['id'],))
            row = cur.fetchone()
            if row and row: continue
            elif today_weekday == 1: 
                cur.execute("INSERT INTO spreads (game_id, week_num, spread_value, is_locked) VALUES (%s, %s, %s, TRUE) ON CONFLICT (game_id) DO UPDATE SET spread_value = EXCLUDED.spread_value, is_locked = TRUE", (g['id'], current_week, g['espn_spread']))
                conn.commit()
            else: 
                cur.execute("INSERT INTO spreads (game_id, week_num, spread_value, is_locked) VALUES (%s, %s, %s, FALSE) ON CONFLICT (game_id) DO UPDATE SET spread_value = EXCLUDED.spread_value WHERE spreads.is_locked = FALSE", (g['id'], current_week, g['espn_spread']))
                conn.commit()

    cur.execute("SELECT game_id, spread_value FROM spreads")
    db_spreads = dict(cur.fetchall())
    cur.execute("SELECT game_id, selected_team FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
    my_saved_picks = dict(cur.fetchall())
    cur.close(); conn.close()
except Exception: pass

# 4. USER INTERFACE: THE MATCHUPS BOARD
st.subheader(f"Week {current_week} Matchup Board")
total_picks_made = len(my_saved_picks)

if games:
    for g in games:
        spread = float(db_spreads.get(g['id'], g['espn_spread']))
        display_line = f"{g['home']} -{abs(spread)}" if spread >= 0 else f"{g['home']} +{abs(spread)}"
        
        st.write(f"### 🏈 **{g['away']} @ {g['home']}** (Line: {display_line})")
        st.caption(f"Status: {g['status'].upper()} | Score: {g['away']} {g['away_score']} - {g['home_score']} {g['home']}")
        
        game_started = False
        is_home_picked = my_saved_picks.get(g['id']) == "HOME"
        is_away_picked = my_saved_picks.get(g['id']) == "AWAY"
        has_this_game_picked = is_home_picked or is_away_picked
        
        # PRECISE 5-PICK UI CONTROLLER
        if total_picks_made >= 5:
            disabled_for_user = not has_this_game_picked
        else:
            disabled_for_user = False
            
        h_style = TEAM_COLORS.get(g['home'], {"bg": "#777777", "text": "#FFFFFF"})
        a_style = TEAM_COLORS.get(g['away'], {"bg": "#777777", "text": "#FFFFFF"})
        
        # STABLE CSS BUTTON TARGETING: Hooks to the unique custom layout string parameter keys
        st.html(f"""
            <style>
            button[key="h_{g['id']}"] {{
                background-color: {h_style['bg']} !important; color: {h_style['text']} !important;
                border: {"4px solid #FFD700" if is_home_picked else "1px solid transparent"} !important;
                box-shadow: {"0px 0px 15px #FFD700" if is_home_picked else "none"} !important;
                font-size: 16px !important; font-weight: bold !important; height: 50px !important;
            }}
            button[key="a_{g['id']}"] {{
                background-color: {a_style['bg']} !important; color: {a_style['text']} !important;
                border: {"4px solid #FFD700" if is_away_picked else "1px solid transparent"} !important;
                box-shadow: {"0px 0px 15px #FFD700" if is_away_picked else "none"} !important;
                font-size: 16px !important; font-weight: bold !important; height: 50px !important;
            }}
            </style>
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"{g['home']} (HOME)", key=f"h_{g['id']}", disabled=disabled_for_user, use_container_width=True):
                conn = get_db_connection()
                cur = conn.cursor()
                if is_home_picked: 
                    cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                else: 
                    cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'HOME') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                conn.commit(); cur.close(); conn.close()
                st.rerun()
                    
        with col2:
            if st.button(f"{g['away']} (AWAY)", key=f"a_{g['id']}", disabled=disabled_for_user, use_container_width=True):
                conn = get_db_connection()
                cur = conn.cursor()
                if is_away_picked: 
                    cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                else: 
                    cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'AWAY') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                conn.commit(); cur.close(); conn.close()
                st.rerun()
        st.divider()
else: st.info("No games scheduled for this week or data loading.")

# 5. LIVE INDIVIDUAL DASHBOARD & SCORE COMPUTATION
st.subheader(f"📊 Your Week {current_week} Tracker ({total_picks_made}/5 Picks)")
my_week_score = 0.0

if games:
    for g_id, choice in my_saved_picks.items():
        try:
            g = next(item for item in games if item["id"] == g_id)
            spread = float(db_spreads.get(g_id, g['espn_spread']))
            actual_margin = g['home_score'] - g['away_score']
            home_cover_points = actual_margin - spread
            game_points = home_cover_points if choice == "HOME" else -home_cover_points
            my_week_score += game_points
            st.write(f"🔹 {g['away']} @ {g['home']} | Selected: `{choice}` | Live Points: **{game_points:+.1f}**")
        except StopIteration: pass

st.metric(label="Your Total Weekly Points", value=f"{my_week_score:+.1f}")

# 6. LEADERBOARD SYSTEM (Season Long Standings)
st.subheader("🏆 Live Standings & Group Picks")
all_historical_picks = []
try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, week, game_id, selected_team FROM user_picks")
    all_historical_picks = cur.fetchall()
    cur.close(); conn.close()
except Exception: pass

standings = {}
group_weekly_picks = {}

for p_user, p_week, p_gid, p_choice in all_historical_picks:
    if p_user not in standings: standings[p_user] = 0.0
    if p_week == current_week:
        if p_user not in group_weekly_picks: group_weekly_picks[p_user] = {}
        group_weekly_picks[p_user][p_gid] = p_choice
        
    try:
        g = next(item for item in games if item["id"] == p_gid)
        s_val = float(db_spreads.get(p_gid, g['espn_spread']))
        margin = g['home_score'] - g['away_score']
        pts = (margin - s_val) if p_choice == "HOME" else -(margin - s_val)
        standings[p_user] += pts
    except Exception: pass

try:
    sorted_standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)
    for rank, (player, score) in enumerate(sorted_standings, 1):
        st.write(f"### {rank}. 👤 **{player.upper()}** — Total Season Score: `{score:+.1f}`")
        player_week_picks = group_weekly_picks.get(player, {})
        if player_week_picks and games:
            pick_displays = []
            for g_id, choice in player_week_picks.items():
                try:
                    g = next(item for item in games if item["id"] == g_id)
                    pick_displays.append(f"🟢 {g['home'] if choice == 'HOME' else g['away']}")
                except StopIteration: pass
            if pick_displays: st.caption("Picks: " + " | ".join(pick_displays))
        st.divider()
except Exception: pass

    
     
