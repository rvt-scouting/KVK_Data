import streamlit as st
import pandas as pd
import psycopg2

st.set_page_config(page_title="Scouting App", page_icon="⚽", layout="wide")
st.title("⚽ Voetbal Data Analyse")

# --- 1. SETUP & VERBINDING ---
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

# --- 2. SIDEBAR FILTERS (CONTEXT) ---
st.sidebar.header("1. Selecteer Data")

# Stap A: Seizoen
season_query = "SELECT DISTINCT season FROM public.iterations ORDER BY season DESC;"
df_seasons = run_query(season_query)
seasons_list = df_seasons['season'].tolist()
selected_season = st.sidebar.selectbox("Seizoen:", seasons_list)

# Stap B: Competitie
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

st.sidebar.divider() # Een lijntje

# --- 3. SIDEBAR MODUS (DE SCHAKELAAR) ---
st.sidebar.header("2. Analyse Niveau")
# Hier maken we de keuze. We gebruiken 'radio' knoppen omdat je er maar 1 tegelijk mag kiezen.
analysis_mode = st.sidebar.radio(
    "Wat wil je analyseren?",
    ["Spelers", "Teams", "Coaches"]
)

# --- 4. DATA OPHALEN (CONTEXT) ---
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
        # We tonen even klein bovenaan welke competitie actief is
        st.info(f"Je kijkt nu naar: **{selected_competition}** ({selected_season})")
    else:
        st.error("Kon geen ID vinden voor deze competitie.")
        st.stop() # Stop de app als er geen ID is
else:
    st.warning("👈 Kies eerst een seizoen en competitie in het menu links.")
    st.stop() 


# --- 5. HOOFDSCHERM LOGICA ---
# Hier kijken we naar de stand van de schakelaar

if analysis_mode == "Spelers":
    st.header("🏃‍♂️ Speler Analyse")
    st.write("Hier komen straks de tabellen en grafieken voor spelers.")
    st.write(f"Data wordt opgehaald voor Iteration ID: `{selected_iteration_id}`")
    
    # TIJDELIJK: Even laten zien dat we klaar zijn voor de volgende stap
    st.success("Module 'Spelers' is actief. We kunnen nu filters gaan bouwen.")

elif analysis_mode == "Teams":
    st.header("🛡️ Team Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")
    st.write("Hier tonen we later data uit `analysis.squad_final_scores`.")

elif analysis_mode == "Coaches":
    st.header("👔 Coach Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")
    st.write("Hier tonen we later data over de technische staf.")
