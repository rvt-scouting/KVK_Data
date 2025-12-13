import streamlit as st
import pandas as pd
import psycopg2

# -----------------------------------------------------------------------------
# 1. CONFIGURATIE & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Scouting App", page_icon="⚽", layout="wide")
st.title("⚽ Voetbal Data Analyse")

# Database connectie functie (gecached)
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["dbname"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"]
    )

# Functie om queries uit te voeren
def run_query(query, params=None):
    conn = init_connection()
    # We gebruiken pandas om SQL direct om te zetten naar een DataFrame
    return pd.read_sql(query, conn, params=params)

# -----------------------------------------------------------------------------
# 2. SIDEBAR FILTERS (Context Bepalen)
# -----------------------------------------------------------------------------
st.sidebar.header("1. Selecteer Data")

# Stap A: Seizoen Selecteren
season_query = "SELECT DISTINCT season FROM public.iterations ORDER BY season DESC;"
try:
    df_seasons = run_query(season_query)
    seasons_list = df_seasons['season'].tolist()
    selected_season = st.sidebar.selectbox("Seizoen:", seasons_list)
except Exception as e:
    st.error("Kon seizoenen niet laden. Check database connectie.")
    st.stop()

# Stap B: Competitie Selecteren (afhankelijk van seizoen)
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
# 3. SIDEBAR MODUS (De Schakelaar)
# -----------------------------------------------------------------------------
st.sidebar.header("2. Analyse Niveau")
analysis_mode = st.sidebar.radio(
    "Wat wil je analyseren?",
    ["Spelers", "Teams", "Coaches"]
)

# -----------------------------------------------------------------------------
# 4. CONTEXT DATA OPHALEN (Het ID vinden)
# -----------------------------------------------------------------------------
selected_iteration_id = None

if selected_season and selected_competition:
    # We halen het iterationId op om verder te gebruiken
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

# === MODUS: SPELERS ===
if analysis_mode == "Spelers":
    st.header("🏃‍♂️ Speler Analyse")
    
    # --- A. SPELER NAAM FILTER OPHALEN ---
    # We gebruiken quotes rond "playerId" en "iterationId" omdat Postgres streng is
    # We gebruiken kleine letters voor commonname in public.players
    players_query = """
        SELECT DISTINCT p.commonname
        FROM public.players p
        JOIN analysis.final_impect_scores s ON p.id = s."playerId"
        WHERE s."iterationId" = %s
        ORDER BY p.commonname;
    """
    
    try:
        df_players = run_query(players_query, params=(selected_iteration_id,))
        player_names = df_players['commonname'].tolist()
        
        # De Multiselect box
        selected_players = st.multiselect("Zoek specifieke spelers:", player_names)
        
    except Exception as e:
        st.error("Fout bij ophalen spelersnamen.")
        st.write("De database gaf deze foutmelding:")
        st.code(e)
        st.stop()

    # --- B. DATA TONEN ---
    st.divider()
    
    # Basis query voor de tabel
    base_query = """
        SELECT 
            p.commonname as "Speler",
            a.position as "Positie",
            a.cb_kvk_score as "CV Score",
            a.dm_kvk_score as "CVM Score",
            a.cm_kvk_score as "CM Score",
            a.fw_kvk_score as "SP Score"
        FROM analysis.final_impect_scores a
        JOIN public.players p ON a."playerId" = p.id
        WHERE a."iterationId" = %s
    """
    
    # Logica: Filter toepassen of niet?
    if selected_players:
        # JA: Filter op de gekozen namen
        query = base_query + " AND p.commonname IN %s ORDER BY p.commonname"
        params = (selected_iteration_id, tuple(selected_players))
        st.write(f"Toont data voor: {', '.join(selected_players)}")
    else:
        # NEE: Toon top 50
        query = base_query + " LIMIT 50"
        params = (selected_iteration_id,)
        st.info("💡 Tip: Gebruik de zoekbalk hierboven om specifieke spelers te vinden. Hieronder zie je de eerste 50.")

    # Uitvoeren en tonen
    try:
        df_scores = run_query(query, params=params)
        st.dataframe(df_scores, use_container_width=True)
    except Exception as e:
        st.error("Fout bij ophalen scores:")
        st.code(e)

# === MODUS: TEAMS ===
elif analysis_mode == "Teams":
    st.header("🛡️ Team Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")
    st.write("Hier tonen we later data uit `analysis.squad_final_scores`.")

# === MODUS: COACHES ===
elif analysis_mode == "Coaches":
    st.header("👔 Coach Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")
    st.write("Hier tonen we later data over de technische staf.")
