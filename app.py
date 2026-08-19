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
    st.error(f"Database connection error: {e}")

st.set_page_config(page_title="Cover 5 Replica", page_icon="🏈")
st.title("🏈 Free Cover 5 League")

username = st.sidebar.text_input("Enter Your Name:", value="Player1").strip().lower()
current_week = st.sidebar.selectbox("Select NFL Week", list(range(1, 19)), index=0)

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
                kickoff_str = event['date'] 
                espn_spread = 0.0
                if len(comp) > 0 and 'odds' in comp[0] and len(comp[0]['odds']) > 0:
                    details = comp[0]['odds'][0].get('details', '') 
                    if details and "EVEN" not in details.upper() and "-" in details:
                        try:
                            espn_spread = float(details.split("-")[-1].strip())
                        except ValueError:
                            pass
                competitors = comp[0]['competitors']
                home_team, away_team, home_score, away_score = "", "", 0, 0
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
                    "status": status, "kickoff": kickoff_str, "espn_spread": espn_spread
                })
    except Exception:
        pass
        
    if len(games_list) == 0 and week == 1:
        return [
            {"id": "mock_1", "away": "BAL", "home": "KC", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-10T20:20Z", "espn_spread": 3.0},
            {"id": "mock_2", "away": "GB", "home": "PHI", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-11T20:15Z", "espn_spread": 2.5},
            {"id": "mock_3", "away": "PIT", "home": "ATL", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": 3.0},
            {"id": "mock_4", "away": "ARI", "home": "BUF", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": 6.0},
            {"id": "mock_5", "away": "TEN", "home": "CHI", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": 4.0},
            {"id": "mock_6", "away": "NE", "home": "CIN", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": 8.5},
            {"id": "mock_7", "away": "HOU", "home": "IND", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": -2.5},
            {"id": "mock_8", "away": "JAX", "home": "MIA", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": 3.5},
            {"id": "mock_9", "away": "CAR", "home": "NO", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": 4.0},
            {"id": "mock_10", "away": "MIN", "home": "NYG", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T13:00Z", "espn_spread": -1.5},
            {"id": "mock_11", "away": "LV", "home": "LAC", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T16:05Z", "espn_spread": 3.0},
            {"id": "mock_12", "away": "DEN", "home": "SEA", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T16:05Z", "espn_spread": 5.5},
            {"id": "mock_13", "away": "DAL", "home": "CLE", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T16:25Z", "espn_spread": 2.5},
            {"id": "mock_14", "away": "LA", "home": "DET", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T20:20Z", "espn_spread": 3.5},
            {"id": "mock_15", "away": "NYJ", "home": "SF", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-14T20:15Z", "espn_spread": 4.5}
        ]
    return games_list

games = []
try:
    games = get_espn_data(current_week)
except Exception:
    pass

today_weekday = datetime.now().weekday()
db_spreads, my_saved_picks = {}, {}

try:
    conn = get_db_connection()
    cur = conn.cursor()
    if games:
        for g in games:
            cur.execute("SELECT spread_value, is_locked FROM spreads WHERE game_id=%s", (g['id'],))
            row = cur.fetchone()
            if row and row[1]: 
                continue
            elif today_weekday == 1: 
                cur.execute("INSERT INTO spreads (game_id, spread_value, is_locked) VALUES (%s, %s, TRUE) ON CONFLICT (game_id) DO UPDATE SET spread_value = EXCLUDED.spread_value, is_locked = TRUE", (g['id'], g['espn_spread']))
                conn.commit()
            else: 
                cur.execute("INSERT INTO spreads (game_id, spread_value, is_locked) VALUES (%s, %s, FALSE) ON CONFLICT (game_id) DO UPDATE SET spread_value = EXCLUDED.spread_value WHERE spreads.is_locked = FALSE", (g['id'], g['espn_spread']))
                conn.commit()
    cur.execute("SELECT game_id, spread_value FROM spreads")
    db_spreads = dict(cur.fetchall())
    cur.execute("SELECT game_id, selected_team FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
    my_saved_picks = dict(cur.fetchall())
    cur.close()
    conn.close()
except Exception:
    pass

st.subheader(f"Week {current_week} Matchup Board")
total_picks_made = len(my_saved_picks)

if games:
    for g in games:
        spread = float(db_spreads.get(g['id'], g['espn_spread']))
        display_line = f"{g['home']} -{abs(spread)}" if spread >= 0 else f"{g['home']} +{abs(spread)}"
        st.write(f"🏈 **{g['away']} @ {g['home']}** (Line: {display_line})")
        game_started = g['status'] != 'pre'
        is_home_picked = my_saved_picks.get(g['id']) == "HOME"
        is_away_picked = my_saved_picks.get(g['id']) == "AWAY"
        has_this_game_picked = is_home_picked or is_away_picked
        disabled_for_user = game_started or (total_picks_made >= 5 and not has_this_game_picked)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Pick {g['home']}", key=f"btn_h_{g['id']}", disabled=disabled_for_user, type="primary" if is_home_picked else "secondary"):
                conn = get_db_connection()
                cur = conn.cursor()
                if is_home_picked:
                    cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                else:
                    cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'HOME') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                conn.commit()
                cur.close()
                conn.close()
                st.rerun()
        with col2:
            if st.button(f"Pick {g['away']}", key=f"btn_a_{g['id']}", disabled=disabled_for_user, type="primary" if is_away_picked else "secondary"):
                conn = get_db_connection()
                cur = conn.cursor()
                if is_away_picked:
                    cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g['id']))
                else:
                    cur.execute("INSERT INTO user_picks (username, week, game_id, selected_team) VALUES (%s, %s, %s, 'AWAY') ON CONFLICT DO NOTHING", (username, current_week, g['id']))
                conn.commit()
                cur.close()
                conn.close()
                st.rerun()
        st.divider()
else:
    st.info("No games scheduled for this week.")

st.subheader(f"📊 Your Tracker ({total_picks_made}/5 Picks)")
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
            st.write(f"🔹 {g['away']} @ {g['home']} | Chosen: {choice} | Points: **{game_points:+.1f}**")
        except StopIteration:
            pass
st.metric(label="Your Total Weekly Points", value=f"{my_week_score:+.1f}")

st.subheader("🏆 Multi-Week Season Standings")
all_historical_picks = []
try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, week, game_id, selected_team FROM user_picks")
    all_historical_picks = cur.fetchall()
    cur.close()
    conn.close()
except Exception:
    pass

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

try:
    sorted_standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)
    for rank, (player, score) in enumerate(sorted_standings, 1):
        st.write(f"{rank}. 👤 **{player.upper()}** — Total Score: `{score:+.1f}`")
except Exception:
    pass

