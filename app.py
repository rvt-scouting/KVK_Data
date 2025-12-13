import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. CONFIGURATIE & SETUP (KV KORTRIJK BRANDING 🔴⚪)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="KVK Scouting", page_icon="🔴", layout="wide")
st.title("🔴⚪ KV Kortrijk - Data Scouting Platform")

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
        selected_iteration_id = df_details.iloc[0]['id']
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
    
    # --- A. SPELER SELECTIE MET DUPLICAAT CHECK ---
    st.sidebar.header("3. Speler Selectie")
    
    # UPDATE: We gebruiken CAST(s."squadId" AS TEXT) = sq.id
    # Dit zorgt dat de integer s.squadId matcht met de text sq.id
    players_query = """
        SELECT p.commonname, p.id as "playerId", sq.name as "squadName"
        FROM public.players p
        JOIN analysis.final_impect_scores s ON p.id = s."playerId"
        LEFT JOIN public.squads sq ON CAST(s."squadId" AS TEXT) = sq.id
        WHERE s."iterationId" = %s
        ORDER BY p.commonname;
    """
    
    try:
        df_players = run_query(players_query, params=(selected_iteration_id,))
        
        # Stap 1: Unieke namen
        unique_names = df_players['commonname'].unique().tolist()
        selected_player_name = st.sidebar.selectbox("Kies een speler:", unique_names)
        
        # Stap 2: Filteren op de gekozen naam om te zien of er dubbels zijn
        candidate_rows = df_players[df_players['commonname'] == selected_player_name]
        
        final_player_id = None
        
        if len(candidate_rows) > 1:
            # ER ZIJN DUBBELS: Toon extra dropdown
            st.sidebar.warning(f"⚠️ Meerdere spelers gevonden: '{selected_player_name}'.")
            
            # Maak een lijstje van teams, maar filter None eruit (voor spelers zonder team)
            squad_options = [s for s in candidate_rows['squadName'].tolist() if s is not None]
            
            if squad_options:
                selected_squad = st.sidebar.selectbox("Kies team:", squad_options)
                # Pak het ID op basis van naam EN team
                final_player_id = candidate_rows[candidate_rows['squadName'] == selected_squad].iloc[0]['playerId']
            else:
                # Fallback als er wel dubbels zijn maar geen teamnamen bekend
                final_player_id = candidate_rows.iloc[0]['playerId']
            
        elif len(candidate_rows) == 1:
            # GEEN DUBBELS
            final_player_id = candidate_rows.iloc[0]['playerId']
        else:
            st.error("Er ging iets mis met de selectie.")
            st.stop()

    except Exception as e:
        st.error("Fout bij ophalen spelerslijst.")
        st.code(e)
        st.stop()

    # --- B. DATA OPHALEN OP BASIS VAN ID ---
    st.divider()
    
    score_query = """
        SELECT 
            p.commonname,
            a.position,
            -- KVK Hoofdscores
            a.cb_kvk_score, a.wb_kvk_score, a.dm_kvk_score,
            a.cm_kvk_score, a.acm_kvk_score, a.fa_kvk_score, a.fw_kvk_score,
            -- Specifieke Sub-profielen
            a.footballing_cb_kvk_score, a.controlling_cb_kvk_score,
            a.defensive_wb_kvk_score, a.offensive_wingback_kvk_score,
            a.ball_winning_dm_kvk_score, a.playmaker_dm_kvk_score,
            a.box_to_box_cm_kvk_score, a.deep_running_acm_kvk_score,
            a.playmaker_off_acm_kvk_score, a.fa_inside_kvk_score,
            a.fa_wide_kvk_score, a.fw_target_kvk_score,
            a.fw_running_kvk_score, a.fw_finisher_kvk_score
        FROM analysis.final_impect_scores a
        JOIN public.players p ON a."playerId" = p.id
        WHERE a."iterationId" = %s AND a."playerId" = %s
    """
    
    try:
        # Casten naar Python int om zeker te zijn
        p_iter_id = int(selected_iteration_id)
        # Zorg dat final_player_id bestaat en een int is
        if final_player_id is not None:
             p_player_id = int(final_player_id)
        else:
             st.stop()
        
        df_scores = run_query(score_query, params=(p_iter_id, p_player_id))
        
        if not df_scores.empty:
            row = df_scores.iloc[0]
            
            # COMPLETE Mapping
            profile_mapping = {
                # --- KVK HOOFDSCORES ---
                "KVK Centrale Verdediger": row['cb_kvk_score'],
                "KVK Wingback": row['wb_kvk_score'],
                "KVK Verdedigende Mid.": row['dm_kvk_score'],
                "KVK Centrale Mid.": row['cm_kvk_score'],
                "KVK Aanvallende Mid.": row['acm_kvk_score'],
                "KVK Flank Aanvaller": row['fa_kvk_score'],
                "KVK Spits": row['fw_kvk_score'],
                
                # --- SUB PROFIELEN ---
                "Voetballende CV": row['footballing_cb_kvk_score'],
                "Controlerende CV": row['controlling_cb_kvk_score'],
                "Verdedigende Back": row['defensive_wb_kvk_score'],
                "Aanvallende Back": row['offensive_wingback_kvk_score'],
                "Ballenafpakker (CVM)": row['ball_winning_dm_kvk_score'],
                "Spelmaker (CVM)": row['playmaker_dm_kvk_score'],
                "Box-to-Box (CM)": row['box_to_box_cm_kvk_score'],
                "Diepgaande '10'": row['deep_running_acm_kvk_
