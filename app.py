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

# 🎯 RECOVERY CHECK: REPLACE LINES 48 TO 60 WITH THIS BULLETPROOF STREAMLINED BLOCK:
st.sidebar.subheader("👤 Player Login")

# 🔐 Establish unerasable session string buffers
if "saved_username" not in st.session_state:
    st.session_state["saved_username"] = ""
if "saved_password" not in st.session_state:
    st.session_state["saved_password"] = ""

# Tie the inputs directly to the session storage keys so URL refreshes can never clear them
username = st.sidebar.text_input("Enter Username:", value=st.session_state["saved_username"], key="saved_username").strip().lower()
password = st.sidebar.text_input("Enter Password:", value=st.session_state["saved_password"], key="saved_password", type="password").strip()
current_week = st.sidebar.selectbox("Select NFL Week", list(range(1, 19)), index=0)

if "authenticated_user" not in st.session_state:
    st.session_state["authenticated_user"] = False

is_logged_in = st.session_state["authenticated_user"]

if username and password and not is_logged_in:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT password_hash FROM user_profiles WHERE username = %s", (username,))
                row = cur.fetchone()
                
                if row:
                    # Account exists: Verify matching key credentials
                    if row[0] == password:  # ✅ Keep your working database index mapping
                        st.session_state["authenticated_user"] = True
                        is_logged_in = True
                        st.sidebar.success(f"🔓 Authenticated: {username.upper()}")
                    else:
                        st.sidebar.error("❌ Invalid password for this profile.")
                else:
                    # Account is completely new: Automatically register profile attributes
                    cur.execute("INSERT INTO user_profiles (username, password_hash) VALUES (%s, %s)", (username, password))
                    conn.commit()
                    st.session_state["authenticated_user"] = True
                    is_logged_in = True
                    st.sidebar.success(f"🆕 Profile Created: Welcome {username.upper()}!")
    except Exception as e:
        st.sidebar.error(f"Login structural crash: {e}")
elif is_logged_in:
    st.sidebar.success(f"🔓 Authenticated: {username.upper()}")
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
        try:
            # Fallback path directly targets ESPN's official 2026 regular season database structure
            fallback_url = f"https://espn.com{week}"
            res_backup = requests.get(fallback_url).json()
            
            if 'events' in res_backup:
                for event in res_backup['events']:
                    comp = event['competitions'][0]
                    status = event['status']['type']['state']
                    kickoff_str = event['date']
                    
                    competitors = comp['competitors']
                    home_team, away_team, home_score, away_score = "", "", 0, 0
                    for team_data in competitors:
                        team_name = team_data['team']['abbreviation']
                        if team_data['homeAway'] == 'home':
                            home_team = team_name
                        else:
                            away_team = team_name
                            
                    games_list.append({
                        "id": str(event['id']), "home": home_team, "away": away_team,
                        "home_score": home_score, "away_score": away_score,
                        "status": status, "kickoff": kickoff_str, "espn_spread": 0.0
                    })
        except Exception:
            pass

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
    
       # 🎯 REPLACE YOUR ENTIRE LIVE BETTING SLIP HUD LOOP WITH THIS SHARP, NO-BADGE VERSION:
    if my_saved_picks:
        st.markdown("### 🎫 My Live Betting Slip")
        
        # Build a fast mapping directory of live game scoring data rows
        live_games_dict = {g["id"]: g for g in games}
        slip_cols = st.columns(len(my_saved_picks))
        
        for index, (g_id, chosen_team) in enumerate(my_saved_picks.items()):
            with slip_cols[index]:
                raw_spread = db_spreads.get(g_id, 0.0)
                game_obj = live_games_dict.get(g_id)
                
                # 🎨 1. Force the main background to ALWAYS stay the official team color
                style = TEAM_COLORS.get(chosen_team, {"bg": "#333", "text": "#fff"})
                hud_bg = style["bg"]
                hud_text = style["text"]
                
                # Base appearance for pre-game or upcoming slots
                score_color = "#ffffff" # Default pure white text
                hud_status_label = f"LINE: {raw_spread}" if raw_spread < 0 else f"LINE: +{raw_spread}"
                
                # If the game is active or finished, calculate the text color changes
                if game_obj and game_obj["status"] in ["in", "post"]:
                    home_team = game_obj["home"]
                    h_score = game_obj["home_score"]
                    a_score = game_obj["away_score"]
                    
                    actual_margin = h_score - a_score
                    if chosen_team == home_team:
                        cover_margin = actual_margin - raw_spread
                    else:
                        cover_margin = -actual_margin + raw_spread
                        
                    # 🎨 2. Change ONLY the score text color based on positive or negative values
                    if cover_margin > 0:
                        score_color = "#00FF00" # Pure high-contrast green text (no badge)
                        hud_status_label = f"+{cover_margin:.1f} ({a_score}-{h_score})"
                    elif cover_margin < 0:
                        score_color = "#FF3333" # Pure high-contrast red text (no badge)
                        hud_status_label = f"{cover_margin:.1f} ({a_score}-{h_score})"
                    else:
                        score_color = "#ffffff" # Pure white text for a push
                        hud_status_label = f"0.0 ({a_score}-{h_score})"
                        
                    if game_obj["status"] == "post":
                        hud_status_label += " (FINAL)"

                # Renders the single-layer clean tile block
                st.markdown(
                    f"""<div style='background-color:{hud_bg}; color:{hud_text}; 
                    padding:12px 4px; border-radius:8px; text-align:center; font-weight:bold; 
                    box-shadow: 0px 4px 10px rgba(0,0,0,0.3); font-size:13px; min-height:65px;'>
                        <div>🏈 {chosen_team}</div>
                        <div style='font-size:12px; margin-top:5px; color:{score_color}; font-family:monospace;'>
                            {hud_status_label}
                        </div>
                    </div>""", 
                    unsafe_allow_html=True
                )
        st.divider()

    # 🎯 PASTE THIS TOTAL POINTS TRACKER CARD OVER THAT PROGRESS BAR SECTION:
    current_pick_count = len(my_saved_picks)
    progress_percentage = min(current_pick_count / 5, 1.0)
    
    # Initialize total score calculation variables
    total_live_points = 0
    live_games_dict = {g["id"]: g for g in games}
    
    # Loop over your selected slips to aggregate the live point scores
    for g_id, chosen_team in my_saved_picks.items():
        game_obj = live_games_dict.get(g_id)
        if game_obj and game_obj["status"] in ["in", "post"]:
            raw_spread = db_spreads.get(g_id, game_obj["espn_spread"])
            h_score = game_obj["home_score"]
            a_score = game_obj["away_score"]
            
            # Run the core point spread valuation formula
            actual_margin = h_score - a_score
            if chosen_team == game_obj["home"]:
                cover_margin = actual_margin - raw_spread
            else:
                cover_margin = -actual_margin + raw_spread
                
            # Tally up points based on cover thresholds
            if cover_margin > 0:
                total_live_points += 5
            elif cover_margin < 0:
                total_live_points -= 5

    # Render a high-contrast layout row splitting the progress tracking and point metrics
    hud_cols = st.columns([2, 1])
    
    with hud_cols[0]:
        st.progress(progress_percentage)
        if current_pick_count == 5:
            st.caption("🎉 **Ticket Status:** 5 teams securely locked in.")
        else:
            st.caption(f"🎫 **Ticket Status:** {current_pick_count} of 5 slots claimed. ({5 - current_pick_count} left)")
            
    with hud_cols[1]:
        # Formulate a dynamic visual text color tag matching your live standing point totals
        if total_live_points > 0:
            score_color = "#125740"  # Vibrant Green for positive scores
            score_label = f"+{total_live_points} pts"
        elif total_live_points < 0:
            score_color = "#e31837"  # High-Alert Red for negative scores
            score_label = f"{total_live_points} pts"
        else:
            score_color = "#475569"  # Neutral Slate for even scores
            score_label = "0 pts"
            
        st.markdown(
            f"""<div style='background-color:{score_color}; color:#fff; padding:6px; 
            border-radius:6px; text-align:center; font-weight:900; font-size:16px; 
            box-shadow: 0px 3px 8px rgba(0,0,0,0.25); margin-top:-5px;'>
            {score_label}
            <div style='font-size:9px; font-weight:bold; opacity:0.85; margin-top:2px;'>WEEKLY TOTAL</div>
            </div>""", 
            unsafe_allow_html=True
        )

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

    # 🎯 PASTE THIS REPLACEMENT SEGMENT IN ITS EXACT PLACE:
        with st.container(border=True):
            status_state = game["status"].lower()
            spread_str = f"{spread}" if spread < 0 else f"+{spread}"
            
            # Generate premium sports-app badge configurations
            if status_state == "in":
                badge_html = "<span style='background-color:#E31837;color:white;padding:2px 6px;border-radius:12px;font-size:10px;font-weight:bold;'>● LIVE</span>"
            elif status_state == "post":
                badge_html = "<span style='background-color:#555555;color:white;padding:2px 6px;border-radius:12px;font-size:10px;font-weight:bold;'>FINAL</span>"
            else:
                badge_html = "<span style='background-color:#125740;color:white;padding:2px 6px;border-radius:12px;font-size:10px;font-weight:bold;'>UPCOMING</span>"
 
    # 🎯 INJECT COMPACT FOOTBALL SCORE TICKER LOGIC HERE:
            score_text_html = ""
            if status_state in ["in", "post"]:
                score_text_html = f"<div style='text-align:center;font-size:15px;font-weight:900;color:#FFF;margin:3px 0;'>{game['away_score']} - {game['home_score']}</div>"

            # 🎯 REPLACE YOUR CODES BOTTOM TWO TEMPLATE LINES (339-341) WITH THESE:
            if current_pick:
                center_display_html = f"<div style='text-align:center;color:#FFD700;font-size:12px;font-weight:bold;margin-bottom:2px;'>🎯 SELECTED</div><div style='text-align:center;margin-bottom:2px;'>{badge_html}</div>{score_text_html}<div style='text-align:center;font-size:11px;font-weight:bold;color:#aaa;'>LINE: {spread_str}</div>"
            else:
                center_display_html = f"<div style='text-align:center;margin-bottom:2px;'>{badge_html}</div>{score_text_html}<div style='text-align:center;font-size:13px;font-weight:bold;color:#888;'>LINE: {spread_str}</div>"
          
                                                                       # 🎯 REPLACE YOUR LOWER COLUMNS LOGIC AT THE BOTTOM OF BOX 2 WITH THIS DEFINITIVE REPAIR:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Clean native text label—zero HTML code text inside the parameters!
                if st.button(f"{game['away']} (AWAY)", key=f"team_btn_away_{g_id}", disabled=is_game_locked, use_container_width=True):
                    if save_pick(g_id, game["away"]):
                        st.rerun()
                        
            with col2:
                # Displays center points and live score states cleanly
                st.markdown(f"<div style='margin-top:2px;'>{center_display_html}</div>", unsafe_allow_html=True)
                if current_pick:
                    if st.button("❌ Clear", key=f"clear_click_action_{g_id}", disabled=is_game_locked, use_container_width=True):
                        with get_db_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM user_picks WHERE username=%s AND week=%s AND game_id=%s", (username, current_week, g_id))
                                conn.commit()
                        st.rerun()
                        
            with col3:
                # Clean native text label—zero HTML code text inside the parameters!
                if st.button(f"{game['home']} (HOME)", key=f"team_btn_home_{g_id}", disabled=is_game_locked, use_container_width=True):
                    if save_pick(g_id, game["home"]):
                        st.rerun()

            # --- 🎨 THE INDEPENDENT STRUCTURAL COLOR ANCHOR SYSTEM ---
            # Streamlit embeds widget keys directly into class lookups (e.g. st-key-team_btn_away_...)
            # This forces the button backgrounds to paint with your exact team hex colors without failing.
            st.markdown(f"""
            <style>
                /* Target the left side button to wrap your away color and frame rules */
                div[class*="st-key-team_btn_away_{g_id}"] button {{
                    background-color: {style_away['bg']} !important;
                    color: {style_away['text']} !important;
                    font-weight: bold !important;
                    border-radius: 6px !important;
                    padding: 12px 5px !important;
                    {away_border}
                }}
                /* Target the right side button to wrap your home color and frame rules */
                div[class*="st-key-team_btn_home_{g_id}"] button {{
                    background-color: {style_home['bg']} !important;
                    color: {style_home['text']} !important;
                    font-weight: bold !important;
                    border-radius: 6px !important;
                    padding: 12px 5px !important;
                    {home_border}
                }}
            </style>
            """, unsafe_allow_html=True)

# =====================================================================
# 📅 BOX 3: TAB 2 WEEKLY LEADERBOARD (FULLY CORRECTED AND ALIGNED)
# =====================================================================
with tab2:
    st.subheader(f"🏈 Week {current_week} Standings & Live Score Tracking")
    
    all_user_picks = []
    all_league_users = set()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                week_filter = int(current_week)
                cur.execute("SELECT username, game_id, selected_team FROM user_picks WHERE week = %s", (week_filter,))
                all_user_picks = cur.fetchall()
                
                cur.execute("SELECT DISTINCT username FROM user_picks")
                # ✅ FIX 1: Safely pull index [0] to flatten database tuples into plain strings
                all_league_users = {row[0].strip().lower() for row in cur.fetchall() if row and row[0]}
    except Exception as e:
        st.error(f"Error compiling leaderboard data: {e}")

    # Ensure current player is tracked even if they have 0 database rows yet
    if username:
        all_league_users.add(username.strip().lower())

    live_games_dict = {g["id"]: g for g in games}
    leaderboard_data = {user: {"Picks Made": 0, "Points": 0, "Details": []} for user in all_league_users}

    # ✅ FIX 2: Indent the loop forward exactly 4 spaces so it renders inside tab2
    for username_item, g_id, selected_team in all_user_picks:
        clean_user_key = str(username_item).strip().lower()
        if clean_user_key not in leaderboard_data:
            continue
        
        # ✅ FIX 3: Route ALL counts and profile adjustments strictly through clean_user_key
        leaderboard_data[clean_user_key]["Picks Made"] += 1
            
        game_obj = live_games_dict.get(g_id)
        if not game_obj:
            if clean_user_key == username:
                leaderboard_data[clean_user_key]["Details"].append(f"{selected_team} (🔒 Pending)")
            else:
                leaderboard_data[clean_user_key]["Details"].append("🔒 Hidden")
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
                
            leaderboard_data[clean_user_key]["Points"] += points_earned
            leaderboard_data[clean_user_key]["Details"].append(f"{selected_team} ({outcome_str})")
        else:
            if clean_user_key == username:
                leaderboard_data[clean_user_key]["Details"].append(f"{selected_team} (🔒 Pending)")
            else:
                leaderboard_data[clean_user_key]["Details"].append("🔒 Hidden")

    started_games_count = sum(1 for g in games if g["status"] in ["in", "post"])

    for player, stats in leaderboard_data.items():
        picks_shortfall = 5 - stats["Picks Made"]
        if picks_shortfall > 0 and started_games_count > 0:
            applicable_penalties = min(picks_shortfall, started_games_count)
            stats["Points"] += (applicable_penalties * -7)
            for _ in range(applicable_penalties):
                stats["Details"].append("⚠️ Unchosen (-7)")

      # 🎯 PASTE THIS CARD LAYOUT OVER THAT TEXT DATAFRAME IN BOX 3:
    if leaderboard_data:
        sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda x: x[1]["Points"], reverse=True)
        
        for rank, (player, stats) in enumerate(sorted_leaderboard, start=1):
            # Assign special visual medal signposts for league leaders
            if rank == 1: medal = "🥇"
            elif rank == 2: medal = "🥈"
            elif rank == 3: medal = "🥉"
            else: medal = f"#{rank}"
            
            tracking_details = "No choices locked yet"
            if stats["Details"]:
                tracking_details = ", ".join(str(d) for d in stats["Details"])
                
            # Render each user profile inside an independent container box
            with st.container(border=True):
                lead_col1, lead_col2 = st.columns([1, 2])
                with lead_col1:
                    st.markdown(f"## {medal}")
                    st.markdown(f"**{player.upper()}**")
                with lead_col2:
                    st.metric(label="Live Score Standing", value=f"{stats['Points']} pts", delta=f"{stats['Picks Made']} / 5 Picks")
                    st.caption(f"🎯 **Ticket Tracking:** {tracking_details}")

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
