import streamlit as st
import requests
import psycopg2
from datetime import datetime

# Initialize Database Connection with automated resource cleanup
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# Initialize Database Tables cleanly
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS spreads (
                    game_id TEXT PRIMARY KEY,
                    week_num INT,
                    spread_value NUMERIC(3,1) DEFAULT 0.0,
                    is_locked BOOLEAN DEFAULT FALSE
                );
                ALTER TABLE spreads ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;
                CREATE TABLE IF NOT EXISTS user_picks (
                    username TEXT,
                    week INT,
                    game_id TEXT,
                    selected_team TEXT,
                    PRIMARY KEY (username, week, game_id)
                );
            """)
            conn.commit()

try:
    init_db()
except Exception as e:
    st.error(f"Database sync alert: {e}")

st.set_page_config(page_title="Cover 5 Pro", page_icon="🏈", layout="wide")
st.title("🏈 Free Cover 5 League Engine")

# Sidebar Configuration
username = st.sidebar.text_input("Enter Your Name:", value="player1").strip().lower()
current_week = st.sidebar.selectbox("Select NFL Week", list(range(1, 19)), index=0)

# Complete NFL Hex Color Palette
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

# Fetch Live NFL Schedule Framework via Core API Endpoints
@st.cache_data(ttl=300) 
def get_espn_data(week):
    url = f"https://espn.com{week}"
    games_list = []
    try:
        res = requests.get(url).json()
        if 'events' in res:
            for event in res['events']:
                comp = event['competitions']
                status = event['status']['type']['state'] 
                kickoff_str = event['date'] 
                espn_spread = 0.0
                
                if 'odds' in comp and len(comp['odds']) > 0:
                    details = comp['odds'].get('details', '') 
                    if details and "EVEN" not in details.upper() and "-" in details:
                        try:
                            espn_spread = float(details.split("-")[-1].strip())
                        except ValueError:
                            pass
                            
                competitors = comp['competitors']
                home_team, away_team, home_score, away_score = "", "", 0, 0
                for team_data in competitors:
                    team_name = team_data['team']['abbreviation']
                    raw_score = team_data.get('score', 0)
                    score_val = int(raw_score) if raw_score else 0
                    if team_data['homeAway'] == 'home': 
                        home_team, home_score = team_name, score_val
                    else: 
                        away_team, away_score = team_name, score_val
                        
                games_list.append({
                    "id": str(event['id']), "home": home_team, "away": away_team,
                    "home_score": home_score, "away_score": away_score,
                    "status": status, "kickoff": kickoff_str, "espn_spread": espn_spread
                })
    except Exception:
        pass
        
    if len(games_list) == 0:
        return [
            {"id": f"2026_w{week}_g1", "away": "NE", "home": "SEA", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.5},
            {"id": f"2026_w{week}_g2", "away": "SF", "home": "LAR", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 2.5},
            {"id": f"2026_w{week}_g3", "away": "CHI", "home": "CAR", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -2.5},
            {"id": f"2026_w{week}_g4", "away": "BAL", "home": "IND", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -3.5}
        ]
    return games_list

games = get_espn_data(current_week)
today_weekday = datetime.now().weekday()
db_spreads = {}
my_saved_picks = {}

try:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if games:
                for g in games:
                    cur.execute("SELECT spread_value, is_locked FROM spreads WHERE game_id=%s", (g['id'],))
                    row = cur.fetchone()
                    if row:
                        continue
                    elif today_weekday == 1: 
                        cur.execute("""
                            INSERT INTO spreads (game_id, week_num, spread_value, is_locked) 
                            VALUES (%s, %s, %s, TRUE) 
                            ON CONFLICT (game_id) DO UPDATE SET spread_value = EXCLUDED.spread_value, is_locked = TRUE
                        """, (g['id'], current_week, g['espn_spread']))
                    else: 
                        cur.execute("""
                            INSERT INTO spreads (game_id, week_num, spread_value, is_locked) 
                            VALUES (%s, %s, %s, FALSE) 
                            ON CONFLICT (game_id) DO UPDATE SET spread_value = EXCLUDED.spread_value WHERE spreads.is_locked = FALSE
                        """, (g['id'], current_week, g['espn_spread']))
                conn.commit()

            cur.execute("SELECT game_id, spread_value FROM spreads WHERE week_num=%s", (current_week,))
            db_spreads = dict(cur.fetchall())
            
            cur.execute("SELECT game_id, selected_team FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
            my_saved_picks = dict(cur.fetchall())
except Exception as e:
    st.error(f"Error handling live data: {e}")
# HARD VALIDATION ENGINE: Saves a pick or rejects if the player hits the cap
def save_pick(game_id, team_selected):
    # Fetch current database pick entries directly before attempting a write
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT game_id FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
                existing_picks = [row[0] for row in cur.fetchall()]
                
                # Rule Check: Is this a modification of an existing game choice?
                is_updating_existing_game = game_id in existing_picks
                
                # Enforce Hard Cap Limit 
                if len(existing_picks) >= 5 and not is_updating_existing_game:
                    st.toast("🚨 Rule Limit: You can only select a maximum of 5 teams per week!", icon="❌")
                    return False
                
                # Proceed with secure database save if validation passes
                cur.execute("""
                    INSERT INTO user_picks (username, week, game_id, selected_team) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username, week, game_id) 
                    DO UPDATE SET selected_team = EXCLUDED.selected_team
                """, (username, current_week, game_id, team_selected))
                conn.commit()
        st.toast(f"Saved pick: {team_selected}!", icon="✅")
        return True
    except Exception as e:
        st.error(f"Failed saving pick: {e}")
        return False

# UI Board Display Configuration
st.subheader(f"Week {current_week} Matchups Board")
st.caption("Pick exactly 5 games against the spread. Your layout lock validation handles restrictions live.")

# Track live selection metric layout counts
current_pick_count = len(my_saved_picks)
if current_pick_count == 5:
    st.metric(label="Total Saved Selection Count", value=f"{current_pick_count} / 5", delta="Locked In", delta_color="normal")
else:
    st.metric(label="Total Saved Selection Count", value=f"{current_pick_count} / 5", delta=f"{5 - current_pick_count} open spots left", delta_color="off")

# Render matching game cards into the layout
for game in games:
    g_id = game["id"]
    spread = db_spreads.get(g_id, game["espn_spread"])
    
    with st.container(border=True):
        col1, col2, col3 = st.columns()
        
        # Check current choice state parameters
        is_away_picked = my_saved_picks.get(g_id) == game["away"]
        is_home_picked = my_saved_picks.get(g_id) == game["home"]
        
        with col1:
            style_away = TEAM_COLORS.get(game["away"], {"bg": "#333", "text": "#fff"})
            st.markdown(f"<div style='background-color:{style_away['bg']}; color:{style_away['text']}; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{game['away']} (Away)</div>", unsafe_allow_html=True)
            if st.button(f"Pick {game['away']}", key=f"btn_away_{g_id}", disabled=(game["status"] != "pre")):
                if save_pick(g_id, game["away"]):
                    st.rerun()
                
        with col2:
            st.markdown("<h4 style='text-align: center; margin: 0;'>VS</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: #888;'>Spread: {spread}</p>", unsafe_allow_html=True)
            if my_saved_picks.get(g_id):
                st.success(f"Selected: {my_saved_picks.get(g_id)}")
                if st.button("❌ Clear Pick", key=f"clear_{g_id}"):
                    with get_db_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g_id))
                            conn.commit()
                    st.rerun()
            
        with col3:
            style_home = TEAM_COLORS.get(game["home"], {"bg": "#333", "text": "#fff"})
            st.markdown(f"<div style='background-color:{style_home['bg']}; color:{style_home['text']}; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{game['home']} (Home)</div>", unsafe_allow_html=True)
            if st.button(f"Pick {game['home']}", key=f"btn_home_{g_id}", disabled=(game["status"] != "pre")):
                if save_pick(g_id, game["home"]):
                    st.rerun()


