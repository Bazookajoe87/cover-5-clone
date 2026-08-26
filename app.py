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
                CREATE TABLE IF NOT EXISTS user_profiles (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL
                );

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
st.title("🏈 Cover 5 Clone")

# 🎯 REPLACE YOUR SIDEBAR NAME BOX WITH THIS AUTHENTICATION CHECK:
st.sidebar.subheader("👤 Player Login")
username = st.sidebar.text_input("Enter Username:", value="").strip().lower()
password = st.sidebar.text_input("Enter Password:", value="", type="password").strip()
current_week = st.sidebar.selectbox("Select NFL Week", list(range(1, 19)), index=0)

is_logged_in = False

if username and password:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT password_hash FROM user_profiles WHERE username = %s", (username,))
                row = cur.fetchone()
                
                if row:
                    # Account exists: Verify matching key credentials
                    if row[0] == password:
                        is_logged_in = True
                        st.sidebar.success(f"🔓 Authenticated: {username.upper()}")
                    else:
                        st.sidebar.error("❌ Invalid password for this profile.")
                else:
                    # Account is completely new: Automatically register profile attributes
                    cur.execute("INSERT INTO user_profiles (username, password_hash) VALUES (%s, %s)", (username, password))
                    conn.commit()
                    is_logged_in = True
                    st.sidebar.success(f"🆕 Profile Created: Welcome {username.upper()}!")
    except Exception as e:
        st.sidebar.error(f"Login structural crash: {e}")
elif username and not password:
    st.sidebar.info("🔑 Please supply a password to unlock your card choices.")

# =====================================================================
# 🔐 ADMIN LOG-IN PROTECTOR CONTROLS (PLACE IN BOX 1)
# =====================================================================
st.sidebar.divider()
is_admin = False

# Simple secret gate: Create a toggle dropdown field to uncover admin settings
show_admin_login = st.sidebar.checkbox("⚙️ League Admin Tools")

if show_admin_login:
    # Set your secret passcode here (change 'cover5admin' to whatever you want)
    admin_password = st.sidebar.text_input("Enter Admin Passcode:", type="password")
    
    if admin_password == "cover5admin":
        is_admin = True
        st.sidebar.success("🔑 Admin Access Verified!")
    elif admin_password != "":
        st.sidebar.error("❌ Incorrect Passcode")

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

# 🚨 UPDATE YOUR PURGE SYSTEM SO IT ONLY LOADS IF ACCESS IS VERIFIED:
if is_admin:
    st.sidebar.subheader("⚠️ Dangerous Maintenance Actions")
    if st.sidebar.button("🗑️ Purge Test User 'player1' Permanently"):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM user_picks WHERE LOWER(TRIM(username)) = 'player1'")
                    conn.commit()
            st.toast("🔥 Successfully expunged 'player1' from database record history!", icon="🚀")
            st.rerun()
        except Exception as e:
            st.error(f"Purge failed: {e}")

# Initialize Navigation Tab Framework
tab1, tab2, tab3 = st.tabs(["🏈 Matchups Board", "📅 Weekly Leaderboard", "🏆 Season Standings"])

# 🎯 PLACE THIS LOGIC BLOCK RIGHT BEFORE BOX 2 STARTS:
if not username:
    st.warning("👋 Welcome to Cover 5 Pro! Please type your official league nickname in the left sidebar to unlock the Matchups Board and lock in your picks.")
    st.stop() # Soft-stops Streamlit from rendering the rest of the cards until they type a name

# =====================================================================
# 🏈 BOX 2: TAB 1 MATCHUPS BOARD (NATIVE FIXED CONTAINER CODES)
# =====================================================================

    # 🎯 PASTE THIS AT THE VERY TOP OF BOX 2 (RIGHT AFTER with tab1:):
with tab1:
    if not is_logged_in:
        st.warning("👋 Welcome to Cover 5 Pro! Please look at the left sidebar panel and enter your profile username and password credentials to unlock your board and save card choices.")
        st.stop() 

    def save_pick(game_id, team_selected):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT game_id FROM user_picks WHERE username=%s AND week=%s", (username, current_week))
                    existing_picks = [row for row in cur.fetchall()]
                    
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
    
    # HUD Layout Framework mapping point lines cleanly next to selections
    if my_saved_picks:
        st.markdown("### 🎫 My Current Slip")
        slip_cols = st.columns(len(my_saved_picks))
        for index, (g_id, chosen_team) in enumerate(my_saved_picks.items()):
            with slip_cols[index]:
                raw_spread = db_spreads.get(g_id, 0.0)
                spread_text = f"{raw_spread}" if raw_spread < 0 else f"+{raw_spread}"
                
                style = TEAM_COLORS.get(chosen_team, {"bg": "#333", "text": "#fff"})
                st.markdown(
                    f"""<div style='background-color:{style['bg']}; color:{style['text']}; 
                    padding:8px; border-radius:5px; text-align:center; font-weight:bold; 
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.15); font-size:13px;'>
                    🏈 {chosen_team} ({spread_text})
                    </div>""", 
                    unsafe_allow_html=True
                )
        st.divider()

    current_pick_count = len(my_saved_picks)
    st.caption(f"**Selections:** {current_pick_count} / 5 Slots Filled")

    # Render Matchups Loops
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

        style_away = TEAM_COLORS.get(game["away"], {"bg": "#333", "text": "#fff"})
        style_home = TEAM_COLORS.get(game["home"], {"bg": "#333", "text": "#fff"})
        
        current_pick = my_saved_picks.get(g_id)
        
        # Safe Border Layout Variables (Separated from the text compiler)
        gold_glow_css = "border: 4px solid #FFD700; box-shadow: 0px 0px 8px #FFD700;"
        base_border_css = "border: 1px solid rgba(255,255,255,0.1);"
        
        away_border = gold_glow_css if current_pick == game["away"] else base_border_css
        home_border = gold_glow_css if current_pick == game["home"] else base_border_css

        with st.container(border=True):
            spread_str = f"{spread}" if spread < 0 else f"+{spread}"
            
                     # 🎯 ALSO FLATTEN THIS CENTER TEXT BLOCK:
            if current_pick:
                center_display_html = f"<div style='text-align:center; color:#FFD700; font-size:12px; font-weight:bold; margin-bottom:2px;'>🎯 LOCKED</div><div style='text-align:center; font-size:11px; font-weight:bold; color:#aaa;'>LINE: {spread_str}</div>"
            else:
                center_display_html = f"<div style='text-align:center; font-size:13px; font-weight:bold; color:#888;'>LINE: {spread_str}</div>"
          
              # 🎯 REPLACE YOUR MULTI-LINE TEMPLATE WITH THIS FLAT ONE-LINE VERSION:
            html_template = "<div style='display: flex; justify-content: space-between; align-items: center; padding: 5px 0;'><div style='width: 38%; __AWAY_STYLE__ background-color: __AWAY_BG__; color: __AWAY_TXT__; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 14px;'>__AWAY_TEAM__</div><div style='width: 24%; text-align: center;'>__CENTER_HTML__</div><div style='width: 38%; __HOME_STYLE__ background-color: __HOME_BG__; color: __HOME_TXT__; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 14px;'>__HOME_TEAM__</div></div>"

            # Direct token swap loop restores color formatting values perfectly
            clean_html = html_template \
                .replace("__AWAY_BG__", style_away['bg']) \
                .replace("__AWAY_TXT__", style_away['text']) \
                .replace("__AWAY_STYLE__", away_border) \
                .replace("__AWAY_TEAM__", game['away']) \
                .replace("__CENTER_HTML__", center_display_html) \
                .replace("__HOME_BG__", style_home['bg']) \
                .replace("__HOME_TXT__", style_home['text']) \
                .replace("__HOME_STYLE__", home_border) \
                .replace("__HOME_TEAM__", game['home'])
                
            st.markdown(clean_html, unsafe_allow_html=True)
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button(f"Pick {game['away']}", key=f"btn_away_{g_id}", disabled=is_game_locked, use_container_width=True):
                    if save_pick(g_id, game["away"]):
                        st.rerun()
            with btn_col2:
                if current_pick:
                    if st.button("❌ Clear", key=f"clear_{g_id}", disabled=is_game_locked, use_container_width=True):
                        with get_db_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g_id))
                                conn.commit()
                        st.rerun()
            with btn_col3:
                if st.button(f"Pick {game['home']}", key=f"btn_home_{g_id}", disabled=is_game_locked, use_container_width=True):
                    if save_pick(g_id, game["home"]):
                        st.rerun()

# =====================================================================
# 📅 BOX 3: TAB 2 WEEKLY LEADERBOARD (PLACE DIRECTLY UNDER BOX 2)
# =====================================================================

    # 🎯 PASTE THIS DIRECTLY UNDER THE 'with tab2:' STATEMENT IN BOX 3:
with tab2:
    st.subheader(f"🏈 Week {current_week} Standings & Live Score Tracking")
    
    all_user_picks = []
    all_league_users = set()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Force current_week into an integer to align table index properties
                week_filter = int(current_week)
                
                cur.execute("""
                    SELECT username, game_id, selected_team 
                    FROM user_picks 
                    WHERE week = %s
                """, (week_filter,))
                all_user_picks = cur.fetchall()
                
                cur.execute("SELECT DISTINCT username FROM user_picks")
                
                # 🎯 CHANGE THAT LINE TO THIS:
 all_league_users = {row[0] for row in cur.fetchall() if row}

    except Exception as e:
        st.error(f"Error compiling leaderboard data: {e}")

    live_games_dict = {g["id"]: g for g in games}
    leaderboard_data = {user: {"Picks Made": 0, "Points": 0, "Details": []} for user in all_league_users}

    # 🎯 CHANGE THAT LOOP START TO THIS:
for username_item, g_id, selected_team in all_user_picks:
    clean_user_key = str(username_item).strip().lower()
    if clean_user_key not in leaderboard_data:
        continue
    
    # Ensure the count ticks up using the clean string key:
    leaderboard_data[clean_user_key]["Picks Made"] += 1
        
        leaderboard_data[username_item]["Picks Made"] += 1   
        
        game_obj = live_games_dict.get(g_id)
        if not game_obj:
            continue
        
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

    started_games_count = sum(1 for g in games if g["status"] in ["in", "post"])

    for player, stats in leaderboard_data.items():
        picks_shortfall = 5 - stats["Picks Made"]
        if picks_shortfall > 0 and started_games_count > 0:
            applicable_penalties = min(picks_shortfall, started_games_count)
            stats["Points"] += (applicable_penalties * -7)
            for _ in range(applicable_penalties):
                stats["Details"].append("⚠️ Unchosen (-7)")

    if leaderboard_data:
        # 🎯 CHANGE IT TO THIS TO STABILIZE THE WEEKLY LEADERBOARD SORTING:
        sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda x: x[1]["Points"], reverse=True)
        
        display_rows = []
        for rank, (player, stats) in enumerate(sorted_leaderboard, start=1):
            player_str = player if not isinstance(player, (tuple, list)) else player
            
            display_rows.append({
                "Rank": f"#{rank}",
                "Player": str(player_str).upper(),
                "Total Picks": f"{stats['Picks Made']} / 5",
                "Live Points Score": f"{stats['Points']} pts",
                "Live Pick Tracking": ", ".join(stats["Details"]) if stats["Details"] else "No activity"
            })
            
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
    else:
        st.info("🏈 No picks have been saved by league players for this week yet.")

# =====================================================================
# 🏆 BOX 4: TAB 3 SEASON-LONG STANDINGS (PLACE AT THE ABSOLUTE BOTTOM)
# =====================================================================
with tab3:
    st.subheader("🏆 Over-The-Year Master Standings")
    st.caption("Season cumulative scores tracking absolute performance rankings across all parsed weeks.")
    
    season_picks_raw = []
    season_users = set()
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT username, week, game_id, selected_team FROM user_picks")
                season_picks_raw = cur.fetchall()
                
                cur.execute("SELECT DISTINCT username FROM user_picks")
                season_users = {row for row in cur.fetchall()}
    except Exception as e:
        st.error(f"Error compiling season database data: {e}")

    season_leaderboard = {user: {"Total Points": 0, "Wins": 0, "Losses": 0, "Pushes": 0, "Penalties": 0} for user in season_users}

    if season_picks_raw:
        picks_by_week = {}
        for p_user, p_week, p_gid, p_team in season_picks_raw:
            if p_week not in picks_by_week:
                picks_by_week[p_week] = []
            picks_by_week[p_week].append((p_user, p_gid, p_team))

        for week_idx, user_picks_list in picks_by_week.items():
            week_games = get_espn_data(week_idx)
            week_games_map = {g["id"]: g for g in week_games}
            
            picks_counter_this_week = {user: 0 for user in season_users}
            
            for p_user, p_gid, p_team in user_picks_list:
                if p_user not in season_leaderboard:
                    continue
                
                game_obj = week_games_map.get(p_gid)
                if not game_obj:
                    continue
                    
                picks_counter_this_week[p_user] += 1
                
                if game_obj["status"] in ["in", "post"]:
                    h_score = game_obj["home_score"]
                    a_score = game_obj["away_score"]
                    spread_val = db_spreads.get(p_gid, game_obj["espn_spread"])
                    
                    margin = h_score - a_score
                    
                    if margin == spread_val:
                        season_leaderboard[p_user]["Pushes"] += 1
                    elif (p_team == game_obj["home"] and margin > spread_val) or (p_team == game_obj["away"] and margin < spread_val):
                        season_leaderboard[p_user]["Total Points"] += 5
                        season_leaderboard[p_user]["Wins"] += 1
                    else:
                        season_leaderboard[p_user]["Total Points"] -= 5
                        season_leaderboard[p_user]["Losses"] += 1

            games_started_this_week = sum(1 for g in week_games if g["status"] in ["in", "post"])
            if games_started_this_week > 0:
                for player in season_users:
                    count_made = picks_counter_this_week.get(player, 0)
                    shortfall = 5 - count_made
                    if shortfall > 0:
                        applied = min(shortfall, games_started_this_week)
                        season_leaderboard[player]["Total Points"] += (applied * -7)
                        season_leaderboard[player]["Penalties"] += applied

        # 🎯 CHANGE IT TO THIS TO REPAIR THE SEASON STANDINGS:
        sorted_season = sorted(season_leaderboard.items(), key=lambda x: x[1]["Total Points"], reverse=True)
 
        season_rows = []
        for rank, (player, stats) in enumerate(sorted_season, start=1):
            player_str = player if not isinstance(player, (tuple, list)) else player
            
            season_rows.append({
                "Rank": f"#{rank}",
                "Player": str(player_str).upper(),
                "Overall Score": f"{stats['Total Points']} pts",
                "Record (W-L-P)": f"{stats['Wins']} - {stats['Losses']} - {stats['Pushes']}",
                "Missed Selection Penalties": f"{stats['Penalties']} applied"
            })
            
        st.dataframe(season_rows, use_container_width=True, hide_index=True)
    else:
        st.info("🏆 Historical season data records are currently empty. Complete weekly games to build standings entries!")
