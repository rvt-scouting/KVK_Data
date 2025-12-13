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
    # We gebruiken hier geen cache voor de kleine dropdown queries, 
    # zodat ze altijd up-to-date en snappy zijn.
    conn = init_connection()
    return pd.read_sql(query, conn, params=params)

# --- 2. SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filters")

# Stap A: Seizoen Selecteren
# We halen alle unieke seizoenen op, gesorteerd van nieuw naar oud
season_query = "SELECT DISTINCT season FROM public.iterations ORDER BY season DESC;"
df_seasons = run_query(season_query)
seasons_list = df_seasons['season'].tolist()

selected_season = st.sidebar.selectbox("Kies een Seizoen:", seasons_list)

# Stap B: Competitie Selecteren (afhankelijk van seizoen)
# We halen de competities op die bij het gekozen seizoen horen
if selected_season:
    competition_query = """
        SELECT DISTINCT "competitionName" 
        FROM public.iterations 
        WHERE season = %s 
        ORDER BY "competitionName";
    """
    df_competitions = run_query(competition_query, params=(selected_season,))
    competitions_list = df_competitions['competitionName'].tolist()
    
    selected_competition = st.sidebar.selectbox("Kies een Competitie:", competitions_list)
else:
    selected_competition = None

# --- 3. HOOFDSCHERM: GESELECTEERDE DATA ---

if selected_season and selected_competition:
    # We halen nu de specifieke rij op voor deze combinatie
    # We pakken id, season, competitionName, competitionType, competitionCountryName
    # Let op de dubbele quotes bij kolomnamen met hoofdletters in Postgres!
    details_query = """
        SELECT season, "competitionName", "competitionType", "competitionCountryName", id
        FROM public.iterations 
        WHERE season = %s AND "competitionName" = %s
        LIMIT 1;
    """
    df_details = run_query(details_query, params=(selected_season, selected_competition))

    if not df_details.empty:
        # Het ID opslaan in een variabele voor later gebruik
        selected_iteration_id = df_details.iloc[0]['id']
        
        st.subheader("📋 Huidige Selectie")
        # We tonen de tabel zoals gevraagd
        st.dataframe(df_details, hide_index=True)
        
        # Even voor ons (ontwikkelaars) om te checken of het werkt:
        st.info(f"💾 Systeem ID voor deze competitie: `{selected_iteration_id}`")
        
        st.divider() # Een lijntje voor de netheid
        st.write("Vanaf hier gaan we straks de spelers tonen die horen bij ID:", selected_iteration_id)
        
    else:
        st.warning("Geen details gevonden voor deze selectie.")
else:
    st.info("👈 Begin door links een seizoen en competitie te kiezen.")
