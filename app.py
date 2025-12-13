import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

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

# === 5. HOOFDSCHERM LOGICA ===

if analysis_mode == "Spelers":
    st.header("🏃‍♂️ Speler Analyse")
    
    # --- A. EEN SPELER KIEZEN (DROPDOWN) ---
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
        
        # VERANDERING: Selectbox in plaats van Multiselect voor 1 speler
        selected_player = st.sidebar.selectbox("Zoek een speler:", player_names)
        
    except Exception as e:
        st.error("Fout bij ophalen spelersnamen.")
        st.code(e)
        st.stop()

    # --- B. DATA OPHALEN VOOR DEZE SPELER ---
    st.divider()
    
    # We halen nu de specifieke profiel scores op
    # Ik pak de kolommen uit je analysis.final_impect_scores tabel
    score_query = """
        SELECT 
            p.commonname,
            a.position,
            -- Verdedigende rollen
            a.footballing_cb_kvk_score,
            a.controlling_cb_kvk_score,
            a.defensive_wb_kvk_score,
            a.offensive_wingback_kvk_score,
            -- Middenveld rollen
            a.ball_winning_dm_kvk_score,
            a.playmaker_dm_kvk_score,
            a.box_to_box_cm_kvk_score,
            a.deep_running_acm_kvk_score,
            a.playmaker_off_acm_kvk_score,
            -- Aanvallende rollen
            a.fa_inside_kvk_score,
            a.fa_wide_kvk_score,
            a.fw_target_kvk_score,
            a.fw_running_kvk_score,
            a.fw_finisher_kvk_score
        FROM analysis.final_impect_scores a
        JOIN public.players p ON a."playerId" = p.id
        WHERE a."iterationId" = %s AND p.commonname = %s
    """
    
    try:
        # We halen de data op voor die ene speler
        df_scores = run_query(score_query, params=(selected_iteration_id, selected_player))
        
        if not df_scores.empty:
            # We pakken de eerste (en enige) rij
            row = df_scores.iloc[0]
            
            # --- C. DATA VOORBEREIDEN VOOR PIE CHART ---
            # We maken een dictionary met leesbare namen voor de kolommen
            # Hier koppelen we de database kolomnaam aan een mooi label
            profile_mapping = {
                "Voetballende Verdediger": row['footballing_cb_kvk_score'],
                "Controlerende Verdediger": row['controlling_cb_kvk_score'],
                "Verdedigende Back": row['defensive_wb_kvk_score'],
                "Aanvallende Back": row['offensive_wingback_kvk_score'],
                "Ballenafpakker (CVM)": row['ball_winning_dm_kvk_score'],
                "Spelmaker (CVM)": row['playmaker_dm_kvk_score'],
                "Box-to-Box": row['box_to_box_cm_kvk_score'],
                "Diepgaande '10'": row['deep_running_acm_kvk_score'],
                "Spelmakende '10'": row['playmaker_off_acm_kvk_score'],
                "Buitenspeler (Binnendoor)": row['fa_inside_kvk_score'],
                "Buitenspeler (Buitenom)": row['fa_wide_kvk_score'],
                "Targetman": row['fw_target_kvk_score'],
                "Lopende Spits": row['fw_running_kvk_score'],
                "Afmaker": row['fw_finisher_kvk_score']
            }
            
            # Nu filteren we alle 'None' (lege) waardes en 0 waardes eruit
            # We willen alleen tonen waar de speler daadwerkelijk een rol in heeft
            active_profiles = {k: v for k, v in profile_mapping.items() if v is not None and v > 0}
            
            # We maken hier weer een klein dataframe van voor de grafiek
            df_chart = pd.DataFrame(list(active_profiles.items()), columns=['Profiel', 'Score'])
            
            # --- D. WEERGAVE ---
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader(f"{selected_player}")
                st.write(f"**Positie:** {row['position']}")
                # Toon de ruwe tabel ook nog even (optioneel)
                st.dataframe(df_chart, hide_index=True)
                
            with col2:
                if not df_chart.empty:
                    # De Pie Chart maken met Plotly
                    fig = px.pie(
                        df_chart, 
                        values='Score', 
                        names='Profiel', 
                        title=f'Profielverdeling: {selected_player}',
                        hole=0.4 # Dit maakt er een 'Donut chart' van, ziet er vaak moderner uit
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Geen profielscores gevonden voor deze speler.")
                    
        else:
            st.error("Geen data gevonden voor deze speler.")

    except Exception as e:
        st.error("Er ging iets mis bij het ophalen van de details:")
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
