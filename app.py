import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. CONFIGURATIE & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="KVK Scouting", page_icon="🔴", layout="wide")
st.title("🔴⚪ KV Kortrijk - Data Scouting Platform")

# --- MAPPING VAN POSITIES NAAR METRIC ID'S ---
POSITION_METRICS = {
    "central_defender": {
        "aan_bal": [66, 58, 64, 10, 163],
        "zonder_bal": [103, 93, 32, 94, 17, 65, 92]
    },
    "wingback": {
        "aan_bal": [61, 66, 58, 54, 53, 52, 10, 9, 14],
        "zonder_bal": [68, 69, 17, 70]
    },
    "defensive_midfield": {
        "aan_bal": [60, 10, 163, 44],
        "zonder_bal": [29, 65, 17, 16, 69, 68, 67]
    },
    "central_midfield": {
        "aan_bal": [60, 61, 62, 73, 72, 64, 10, 163, 145],
        "zonder_bal": [65, 17, 69, 68]
    },
    "attacking_midfield": {
        "aan_bal": [60, 61, 62, 73, 58, 2, 15, 52, 72, 10, 74, 9],
        "zonder_bal": [] 
    },
    "winger": {
        "aan_bal": [60, 61, 62, 58, 54, 1, 53, 10, 9, 14, 6, 145],
        "zonder_bal": []
    },
    "center_forward": {
        "aan_bal": [60, 61, 62, 73, 63, 2, 64, 10, 74, 9, 92, 97, 14, 6, 145],
        "zonder_bal": []
    }
}

def get_metrics_for_position(db_position):
    if not db_position:
        return None
    
    pos = str(db_position).upper().strip()
    
    if pos == "CENTRAL_DEFENDER":
        return POSITION_METRICS['central_defender']
    elif pos in ["RIGHT_WINGBACK", "LEFT_WINGBACK"]:
        return POSITION_METRICS['wingback']
    elif pos in ["DEFENSIVE_MIDFIELD", "DEFENSE_MIDFIELD"]:
        return POSITION_METRICS['defensive_midfield']
    elif pos == "CENTRAL_MIDFIELD":
        return POSITION_METRICS['central_midfield']
    elif pos in ["ATTACKING_MIDFIELD", "OFFENSIVE_MIDFIELD"]:
        return POSITION_METRICS['attacking_midfield']
    elif pos in ["RIGHT_WINGER", "LEFT_WINGER"]:
        return POSITION_METRICS['winger']
    elif pos in ["CENTRAL_FORWARD", "STRIKER"]:
        return POSITION_METRICS['center_forward']
    
    return None

@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["dbname"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"]
    )

def run_query(query, params=None):
    conn = init_connection()
    return pd.read_sql(query, conn, params=params)

# -----------------------------------------------------------------------------
# 2. SIDEBAR FILTERS
# -----------------------------------------------------------------------------
st.sidebar.header("1. Selecteer Data")

# Seizoen
season_query = "SELECT DISTINCT season FROM public.iterations ORDER BY season DESC;"
try:
    df_seasons = run_query(season_query)
    seasons_list = df_seasons['season'].tolist()
    selected_season = st.sidebar.selectbox("Seizoen:", seasons_list)
except Exception as e:
    st.error("Kon seizoenen niet laden.")
    st.stop()

# Competitie
if selected_season:
    competition_query = """
        SELECT DISTINCT "competitionName" 
        FROM public.iterations 
        WHERE season = %s 
        ORDER BY "competitionName";
    """
    df_competitions = run_query(competition_query, params=(selected_season,))
    competitions_list = df_competitions['competitionName'].tolist()
    selected_competition = st.sidebar.selectbox("Competitie:", competitions_list)
else:
    selected_competition = None

st.sidebar.divider() 

# -----------------------------------------------------------------------------
# 3. ANALYSE MODUS
# -----------------------------------------------------------------------------
st.sidebar.header("2. Analyse Niveau")
analysis_mode = st.sidebar.radio(
    "Wat wil je analyseren?",
    ["Spelers", "Teams", "Coaches"]
)

# -----------------------------------------------------------------------------
# 4. ITERATION ID OPHALEN
# -----------------------------------------------------------------------------
selected_iteration_id = None

if selected_season and selected_competition:
    details_query = """
        SELECT season, "competitionName", id
        FROM public.iterations 
        WHERE season = %s AND "competitionName" = %s
        LIMIT 1;
    """
    df_details = run_query(details_query, params=(selected_season, selected_competition))

    if not df_details.empty:
        # DIT IS NU TEKST (STRING)
        selected_iteration_id = str(df_details.iloc[0]['id'])
        st.info(f"Je kijkt nu naar: **{selected_competition}** ({selected_season})")
    else:
        st.error("Kon geen ID vinden voor deze competitie.")
        st.stop() 
else:
    st.warning("👈 Kies eerst een seizoen en competitie in het menu links.")
    st.stop() 

# -----------------------------------------------------------------------------
# 5. HOOFDSCHERM LOGICA
# -----------------------------------------------------------------------------

if analysis_mode == "Spelers":
    st.header("🏃‍♂️ Speler Analyse")
    
    # --- A. SPELER SELECTIE ---
    st.sidebar.header("3. Speler Selectie")
    
    # SCHOONMAAK: Geen CAST meer nodig, alles is tekst!
    players_query = """
        SELECT p.commonname, p.id as "playerId", sq.name as "squadName"
        FROM public.players p
        JOIN analysis.final_impect_scores s ON p.id = s."playerId"
        LEFT JOIN public.squads sq ON s."squadId" = sq.id
        WHERE s."iterationId" = %s
        ORDER BY p.commonname;
    """
    
    try:
        # We sturen gewoon de string ID door
        df_players = run_query(players_query, params=(selected_iteration_id,))
        
        unique_names = df_players['commonname'].unique().tolist()
        selected_player_name = st.sidebar.selectbox("Kies een speler:", unique_names)
        
        candidate_rows = df_players[df_players['commonname'] == selected_player_name]
        
        final_player_id = None
        
        if len(candidate_rows) > 1:
            st.sidebar.warning(f"⚠️ Meerdere spelers gevonden: '{selected_player_name}'.")
            squad_options = [s for s in candidate_rows['squadName'].tolist() if s is not None]
            if squad_options:
                selected_squad = st.sidebar.selectbox("Kies team:", squad_options)
                final_player_id = candidate_rows[candidate_rows['squadName'] == selected_squad].iloc[0]['playerId']
            else:
                final_player_id = candidate_rows.iloc[0]['playerId']
        elif len(candidate_rows) == 1:
            final_player_id = candidate_rows.iloc[0]['playerId']
        else:
            st.error("Er ging iets mis met de selectie.")
            st.stop()

    except Exception as e:
        st.error("Fout bij ophalen spelerslijst.")
        st.code(e)
        st.stop()

    # --- B. HOOFD PROFIELEN & BIO ---
    st.divider()
    
    # SCHOONMAAK: Geen CAST meer nodig
    score_query = """
        SELECT 
            p.commonname, a.position, p.birthdate, p.birthplace, p.leg,
            sq_curr.name as "current_team_name",
            a.cb_kvk_score, a.wb_kvk_score, a.dm_kvk_score,
            a.cm_kvk_score, a.acm_kvk_score, a.fa_kvk_score, a.fw_kvk_score,
            a.footballing_cb_kvk_score, a.controlling_cb_kvk_score,
            a.defensive_wb_kvk_score, a.offensive_wingback_kvk_score,
            a.ball_winning_dm_kvk_score, a.playmaker_dm_kvk_score,
            a.box_to_box_cm_kvk_score, a.deep_running_acm_kvk_score,
            a.playmaker_off_acm_kvk_score, a.fa_inside_kvk_score,
            a.fa_wide_kvk_score, a.fw_target_kvk_score,
            a.fw_running_kvk_score, a.fw_finisher_kvk_score
        FROM analysis.final_impect_scores a
        JOIN public.players p ON a."playerId" = p.id
        LEFT JOIN public.squads sq_curr ON p."currentSquadId" = sq_curr.id
        WHERE a."iterationId" = %s AND p.id = %s
    """
    
    try:
        # Zorg dat player ID ook string is
        p_player_id = str(final_player_id)
        
        df_scores = run_query(score_query, params=(selected_iteration_id, p_player_id))
        
        if not df_scores.empty:
            row = df_scores.iloc[0]
            
            # 1. BIO
            st.subheader(f"ℹ️ {selected_player_name}")
            col_bio1, col_bio2, col_bio3, col_bio4 = st.columns(4)
            with col_bio1: st.metric("Huidig Team", row['current_team_name'] if row['current_team_name'] else "Onbekend")
            with col_bio2: st.metric("Geboortedatum", str(row['birthdate']) if row['birthdate'] else "-")
            with col_bio3: st.metric
