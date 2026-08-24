import streamlit as st
import requests
import psycopg2
from datetime import datetime

# =====================================================================
# 🔌 BOX 1: DATABASE SETUP, IMPORTS, AND DATA ENGINE
# =====================================================================
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

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
                ALTER TABLE spreads ADD COLUMN IF NOT EXISTS week_num INT;

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

username = st.sidebar.text_input("Enter Your Name:", value="player1").strip().lower()
current_week = st.sidebar.selectbox("Select NFL Week", list(range(1, 19)), index=0)

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
            {"id": f"26_w{week}_g1", "away": "NE", "home": "SEA", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": 3.5},
            {"id": f"26_w{week}_g2", "away": "SF", "home": "LAR", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T20:25Z", "espn_spread": 2.5},
            {"id": f"26_w{week}_g3", "away": "CHI", "home": "CAR", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": -2.5},
            {"id": f"26_w{week}_g4", "away": "BAL", "home": "IND", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": -3.5},
            {"id": f"26_w{week}_g5", "away": "TB", "home": "CIN", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": 3.5},
            {"id": f"26_w{week}_g6", "away": "ATL", "home": "PIT", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": 1.5},
            {"id": f"26_w{week}_g7", "away": "NYJ", "home": "TEN", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": -1.0},
            {"id": f"26_w{week}_g8", "away": "NO", "home": "DET", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": 6.5},
            {"id": f"26_w{week}_g9", "away": "BUF", "home": "HOU", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": -2.0},
            {"id": f"26_w{week}_g10", "away": "CLE", "home": "JAX", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": 3.0},
            {"id": f"26_w{week}_g11", "away": "ARI", "home": "LAC", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T20:05Z", "espn_spread": 7.5},
            {"id": f"26_w{week}_g12", "away": "GB", "home": "MIN", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T20:25Z", "espn_spread": 1.5},
            {"id": f"26_w{week}_g13", "away": "MIA", "home": "LV", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T20:25Z", "espn_spread": 4.0},
            {"id": f"26_w{week}_g14", "away": "WSH", "home": "PHI", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-13T17:00Z", "espn_spread": 5.5},
            {"id": f"26_w{week}_g15", "away": "DAL", "home": "NYG", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-14T00:20Z", "espn_spread": -3.0},
            {"id": f"26_w{week}_g16", "away": "DEN", "home": "KC", "home_score": 0, "away_score": 0, "status": "pre", "kickoff": "2026-09-15T00:15Z", "espn_spread": 9.5}
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

if st.sidebar.button("🗑️ Clear Corrupted Test Picks"):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
            conn.commit()
    st.rerun()

# Initialize Navigation Tab Framework
tab1, tab2 = st.tabs(["🏈 Matchups Board", "🏆 Live Leaderboard"])

# =====================================================================
# 🏈 BOX 2: TAB 1 MATCHUPS BOARD (PLACE DIRECTLY UNDER BOX 1)
# =====================================================================
with tab1:
    def save_pick(game_id, team_selected):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT game_id FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
                    existing_picks = [row[0] for row in cur.fetchall()]
                    
                    is_updating_existing_game = game_id in existing_picks
                    
                    if len(existing_picks) >= 5 and not is_updating_existing_game:
                        st.toast("🚨 Rule Limit: You can only select a maximum of 5 teams per week!", icon="❌")
                        return False
                    
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

    st.subheader(f"Week {current_week} Matchups Board")
    st.caption("Review all games. Select up to 5 teams against the line. Change picks prior to kickoff.")

    current_pick_count = len(my_saved_picks)
    if current_pick_count == 5:
        st.metric(label="Total Saved Selection Count", value=f"{current_pick_count} / 5", delta="Selections Locked In", delta_color="normal")
    else:
        st.metric(label="Total Saved Selection Count", value=f"{current_pick_count} / 5", delta=f"{5 - current_pick_count} spaces available", delta_color="off")

    for game in games:
        g_id = game["id"]
        spread = db_spreads.get(g_id, game["espn_spread"])
        
        is_game_locked = game["status"] != "pre"
        try:
            if "Z" in game["kickoff"]:
                ko_time = datetime.strptime(game["kickoff"], "%Y-%m-%dT%H:%MfZ")
                if datetime.utcnow() >= ko_time:
                    is_game_locked = True
        except Exception:
            pass

        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                style_away = TEAM_COLORS.get(game["away"], {"bg": "#333", "text": "#fff"})
                st.markdown(f"<div style='background-color:{style_away['bg']}; color:{style_away['text']}; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{game['away']} (Away)</div>", unsafe_allow_html=True)
                if st.button(f"Pick {game['away']}", key=f"btn_away_{g_id}", disabled=is_game_locked, use_container_width=True):
                    if save_pick(g_id, game["away"]):
                        st.rerun()
                    
            with col2:
                st.markdown("<h4 style='text-align: center; margin: 0;'>VS</h4>", unsafe_allow_html=True)
                
                if spread < 0:
                    st.markdown(f"<p style='text-align: center; color: #FB4F14; font-weight: bold; margin: 5px 0;'>🔥 Favorite: {game['away']} ({spread})</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p style='text-align: center; color: #0080C6; font-weight: bold; margin: 5px 0;'>🔥 Favorite: {game['home']} (-{spread})</p>", unsafe_allow_html=True)
                
                if my_saved_picks.get(g_id):
                    st.info(f"👉 Current Choice: **{my_saved_picks.get(g_id)}**")
                    if st.button("❌ Unselect Choice", key=f"clear_{g_id}", disabled=is_game_locked, use_container_width=True):
                        with get_db_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g_id))
                                conn.commit()
                        st.rerun()
                else:
                    st.markdown("<p style='text-align: center; color: #aaa; font-style: italic; margin-top: 5px;'>No Selection</p>", unsafe_allow_html=True)
                
            with col3:
                style_home = TEAM_COLORS.get(game["home"], {"bg": "#333", "text": "#fff"})
                st.markdown(f"<div style='background-color:{style_home['bg']}; color:{style_home['text']}; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{game['home']} (Home)</div>", unsafe_allow_html=True)
                if st.button(f"Pick {game['home']}", key=f"btn_home_{g_id}", disabled=is_game_locked, use_container_width=True):
                    if save_pick(g_id, game["home"]):
                        st.rerun()

# =====================================================================
# 🏆 BOX 3: TAB 2 LEAGUE STANDINGS ENGINE (PLACE AT BOTTOM OF FILE)
# =====================================================================
with tab2:
    st.subheader("🏆 League Standings & Live Score Tracking")
    
    all_user_picks = []
    all_league_users = set()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT username, game_id, selected_team FROM user_picks WHERE week = %s", (current_week,))
                all_user_picks = cur.fetchall()
                
                cur.execute("SELECT DISTINCT username FROM user_picks")
                all_league_users = {row[0] for row in cur.fetchall()}
    except Exception as e:
        st.error(f"Error compiling leaderboard data: {e}")

    if username:
        all_league_users.add(username)

    live_games_dict = {g["id"]: g for g in games}
    leaderboard_data = {user: {"Picks Made": 0, "Points": 0, "Details": []} for user in all_league_users}

    for username_item, g_id, selected_team in all_user_picks:
        if username_item not in leaderboard_data:
            continue
            
        game_obj = live_games_dict.get(g_id)
        if not game_obj:
            continue
            
        leaderboard_data[username_item]["Picks Made"] += 1
        
        if game_obj["status"] in ["in", "post"]:
            home = game_obj["home"]
            away = game_obj["away"]
            h_score = game_obj["home_score"]
            a_score = game_obj["away_score"]
            spread_val = db_spreads.get(g_id, game_obj["espn_spread"])
            
            actual_margin = h_score - a_score
            is_home_winner = actual_margin > spread_val
            is_push = actual_margin == spread_val
            
            if is_push:
                points_earned = 0
                outcome_str = "🤝 Push"
            elif (selected_team == home and is_home_winner) or (selected_team == away and not is_home_winner):
                points_earned = 5
                outcome_str = "✅ Cover (+5)"
            else:
                points_earned = -5
                outcome_str = "❌ Miss (-5)"
                
            leaderboard_data[username_item]["Points"] += points_earned
            leaderboard_data[username_item]["Details"].append(f"{selected_team} ({outcome_str})")
        else:
            if username_item == username:
                leaderboard_data[username_item]["Details"].append(f"{selected_team} (🔒 Pending)")
            else:
                leaderboard_data[username_item]["Details"].append("🔒 Hidden")

    # DESIGN RULE: -7 POINTS FOR EVERY UNCHOSEN MATCHUP SLOT AFTER KICKOFF
    started_games_count = sum(1 for g in games if g["status"] in ["in", "post"])

    for player, stats in leaderboard_data.items():
        picks_shortfall = 5 - stats["Picks Made"]
        
        if picks_shortfall > 0 and started_games_count > 0:
            applicable_penalties = min(picks_shortfall, started_games_count)
            penalty_total = applicable_penalties * -7
            stats["Points"] += penalty_total
            
            for _ in range(applicable_penalties):
                stats["Details"].append("⚠️ Unchosen (-7)")

    if leaderboard_data:
        sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda x: x["Points"], reverse=True)
        
        display_rows = []
        for rank, (player, stats) in enumerate(sorted_leaderboard, start=1):
            display_rows.append({
                "Rank": f"#{rank}",
                "Player": player.upper(),
                "Total Picks": f"{stats['Picks Made']} / 5",
                "Live Points Score": f"{stats['Points']} pts",
                "Live Pick Tracking": ", ".join(stats["Details"]) if stats["Details"] else "No activity"
            })
            
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
    else:
        st.info("🏈 No picks have been saved by league players for this week yet.")
