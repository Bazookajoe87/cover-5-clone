import streamlit as st
import requests
import psycopg2
from datetime import datetime

def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

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
st.title("🏈 Ultimate Cover 5 Autopilot Platform")

username = st.sidebar.text_input("Player Profile Username:", value="Player1").strip().lower()
current_week = st.sidebar.selectbox("NFL Week Selector", list(range(1, 19)), index=0)

@st.cache_data(ttl=300) 
def get_espn_data(week):
    url = f"https://espn.com{week}"
    games_list = []
    try:
        res = requests.get(url).json()
        if 'events' in res and len(res['events']) > 0:
            for event in res['events']:
                comp = event['competitions']
                status = event['status']['type']['state']
                
                espn_spread = 0.0
                if 'odds' in comp and len(comp['odds']) > 0:
                    details = comp['odds'].get('details', '')
                    if details and "EVEN" not in details.upper() and "-" in details:
                        try:
                            espn_spread = float(details.split("-")[-1].strip())
                        except ValueError: pass
                
                competitors = comp['competitors']
                home_team, away_team, home_score, away_score = "", "", 0, 0
                for t in competitors:
                    name = t['team']['abbreviation']
                    score = int(t.get('score', 0)) if t.get('score') else 0
                    if t['homeAway'] == 'home':
                        home_team, home_score = name, score
                    else:
                        away_team, away_score = name, score
                        
                games_list.append({
                    "id": str(event['id']), "home": home_team, "away": away_team,
                    "home_score": home_score, "away_score": away_score,
                    "status": status, "espn_spread": espn_spread
                })
    except Exception: pass
    
    if len(games_list) == 0 and week == 1:
        return [
            {"id": "2026_w1_g1", "away": "NE", "home": "SEA", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.5},
            {"id": "2026_w1_g2", "away": "SF", "home": "LAR", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 2.5},
            {"id": "2026_w1_g3", "away": "CHI", "home": "CAR", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -2.5},
            {"id": "2026_w1_g4", "away": "BAL", "home": "COLS", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -3.5},
            {"id": "2026_w1_g5", "away": "TB", "home": "CIN", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.5},
            {"id": "2026_w1_g6", "away": "ATL", "home": "PIT", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 3.0},
            {"id": "2026_w1_g7", "away": "NYJ", "home": "TEN", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": -1.5},
            {"id": "2026_w1_g8", "away": "NO", "home": "DET", "home_score": 0, "away_score": 0, "status": "pre", "espn_spread": 7.0},
            {"id": "2026_w1_g9", "away": "BUF", "home": "HOU", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "pre", "espn_spread": -1.5},
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
today_weekday = datetime.now().weekday()
db_spreads, my_saved_picks = {}, {}

try:
    conn = get_db_connection()
    cur = conn.cursor()
    if games:
        for g in games:
            cur.execute("SELECT spread_value, is_locked FROM spreads WHERE game_id=%s", (g['id'],))
            row = cur.fetchone()
            if row and row[1]: continue
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
    cur.close()
    conn.close()
except Exception: pass

st.header(f"🏈 Week {current_week} Pick Center Dashboard")
total_picks_made = len(my_saved_picks)

if today_weekday == 1: st.success("🔒 Tuesday Freeze Active: Point spreads are permanently locked.")
else: st.info("🔄 Live Vegas Lines Syncing. Spreads auto-lock this Tuesday.")

if games:
    for g in games:
        spread = float(db_spreads.get(g['id'], g['espn_spread']))
        line_display = f"{g['home']} -{abs(spread)}" if spread >= 0 else f"{g['home']} +{abs(spread)}"
        
        with st.container():
            col_match, col_btn1, col_btn2 = st.columns([2, 1, 1])
            with col_match:
                st.write(f"### {g['away']} @ {g['home']}")
                st.caption(f"Line Baseline: {line_display} | Status: {g['status'].upper()} ({g['away']} {g['away_score']} - {g['home_score']} {g['home']})")
            
            game_started = g['status'] in ['in', 'post']
            is_home_picked = my_saved_picks.get(g['id']) == "HOME"
            is_away_picked = my_saved_picks.get(g['id']) == "AWAY"
            disabled_for_user = game_started or (total_picks_made >= 5 and not (is_home_picked or is_away_picked))
            
            with col_btn1:
                if st.button(f"Take {g['home']}", key=f"h_{g['id']}", disabled=disabled_for_user, type="primary" if is_home_picked else "secondary", use_container_width=True):
                    conn = get_db_connection()
                    cur = conn.cursor()
                    if is_home_picked: cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                    else: cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'HOME') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                    conn.commit(); cur.close(); conn.close(); st.rerun()
            with col_btn2:
                if st.button(f"Take {g['away']}", key=f"a_{g['id']}", disabled=disabled_for_user, type="primary" if is_away_picked else "secondary", use_container_width=True):
                    conn = get_db_connection()
                    cur = conn.cursor()
                    if is_away_picked: cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                    else: cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'AWAY') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                    conn.commit(); cur.close(); conn.close(); st.rerun()
            st.divider()
else: st.info("No games scheduled or loading data feed.")

st.header(f"📊 Your Live Tracker ({total_picks_made}/5 Picks)")
my_week_score = 0.0
if games:
    for g_id, choice in my_saved_picks.items():
        try:
            g = next(item for item in games if item["id"] == g_id)
            spread = float(db_spreads.get(g_id, g['espn_spread']))
            margin = g['home_score'] - g['away_score']
            home_pts = margin - spread
            game_points = home_pts if choice == "HOME" else -home_pts
            my_week_score += game_points
            st.write(f"🔹 **{g['away']} @ {g['home']}** | Picked: `{choice}` | Live Points: **{game_points:+.1f}**")
        except StopIteration: pass
st.metric(label="Your Combined Weekly Margin Score", value=f"{my_week_score:+.1f}")

st.header("🏆 Live Multi-Week Season Standings")
try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, week, game_id, selected_team FROM user_picks")
    all_historical_picks = cur.fetchall()
    cur.close(); conn.close()
    
    standings = {}
    for p_user, p_week, p_gid, p_choice in all_historical_picks:
        if p_user not in standings: standings[p_user] = 0.0
        try:
            hist_games = get_espn_data(p_week)
            g = next(item for item in hist_games if item["id"] == p_gid)
            s_val = float(db_spreads.get(p_gid, g['espn_spread']))
            margin = g['home_score'] - g['away_score']
            pts = (margin - s_val) if p_choice == "HOME" else -(margin - s_val)
            standings[p_user] += pts
        except Exception: pass
        
    sorted_standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)
    for rank, (player, score) in enumerate(sorted_standings, 1):
        st.write(f"{rank}. 👤 **{player.upper()}** — Cumulative Total: `{score:+.1f}`")
except Exception: pass
