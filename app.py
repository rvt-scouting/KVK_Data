import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. CONFIGURATIE & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Scouting App", page_icon="⚽", layout="wide")
st.title("⚽ Voetbal Data Analyse")

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
    
    # --- A. SPELER SELECTIE ---
    st.sidebar.header("3. Speler Selectie")
    
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
        selected_player = st.sidebar.selectbox("Kies een speler:", player_names)
        
    except Exception as e:
        st.error("Fout bij ophalen spelersnamen.")
        st.stop()

    # --- B. DATA OPHALEN ---
    st.divider()
    
    score_query = """
        SELECT 
            p.commonname,
            a.position,
            a.footballing_cb_kvk_score, a.controlling_cb_kvk_score,
            a.defensive_wb_kvk_score, a.offensive_wingback_kvk_score,
            a.ball_winning_dm_kvk_score, a.playmaker_dm_kvk_score,
            a.box_to_box_cm_kvk_score, a.deep_running_acm_kvk_score,
            a.playmaker_off_acm_kvk_score, a.fa_inside_kvk_score,
            a.fa_wide_kvk_score, a.fw_target_kvk_score,
            a.fw_running_kvk_score, a.fw_finisher_kvk_score
        FROM analysis.final_impect_scores a
        JOIN public.players p ON a."playerId" = p.id
        WHERE a."iterationId" = %s AND p.commonname = %s
    """
    
    try:
        df_scores = run_query(score_query, params=(selected_iteration_id, selected_player))
        
        if not df_scores.empty:
            row = df_scores.iloc[0]
            
            # Mapping maken
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
            
            # Filteren
            active_profiles = {k: v for k, v in profile_mapping.items() if v is not None and v > 0}
            df_chart = pd.DataFrame(list(active_profiles.items()), columns=['Profiel', 'Score'])
            
            # --- C. DE BEREKENINGEN (Highlight & Callout) ---
            
            # 1. Zoek de hoogste score
            top_profile_name = None
            top_profile_score = 0
            
            if not df_chart.empty:
                # Sorteer zodat de hoogste bovenaan staat (voor de zekerheid)
                df_chart = df_chart.sort_values(by='Score', ascending=False)
                
                highest_row = df_chart.iloc[0]
                if highest_row['Score'] > 66:
                    top_profile_name = highest_row['Profiel']
                    top_profile_score = highest_row['Score']

            # 2. Styling Functie voor de Tabel
            def highlight_high_scores(val):
                """Maakt de tekst groen en vetgedrukt als score > 66"""
                if isinstance(val, (int, float)) and val > 66:
                    return 'color: #2ecc71; font-weight: bold' # Mooi fel groen
                return ''

            # --- D. WEERGAVE ---
            
            # Eerst de Callout tonen (groot bovenaan het blok)
            if top_profile_name:
                st.success(f"### ✅ Speler is POSITIEF op data profiel: {top_profile_name}")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader(f"{selected_player}")
                st.write(f"**Positie:** {row['position']}")
                st.write("Score per profiel:")
                
                # Pas de styling toe op de tabel
                # We formatteren de getallen ook meteen met 1 decimaal (indien nodig)
                st.dataframe(
                    df_chart.style.applymap(highlight_high_scores, subset=['Score'])
                            .format({'Score': '{:.1f}'}),
                    use_container_width=True,
                    hide_index=True
                )
                
            with col2:
                if not df_chart.empty:
                    # De Pie Chart met aangepaste kleuren
                    fig = px.pie(
                        df_chart, 
                        values='Score', 
                        names='Profiel', 
                        title=f'Profielverdeling',
                        hole=0.4,
                        # Hier stellen we de kleuren in:
                        color_discrete_sequence=['#e74c3c', '#ecf0f1', '#3498db'] # Rood, Wit (beetje grijs voor zichtbaarheid), Blauw
                    )
                    # Zorg dat de witte tekst leesbaar is of randjes heeft
                    fig.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Geen actieve profielscores gevonden.")
                    
        else:
            st.error("Geen data gevonden voor deze speler.")

    except Exception as e:
        st.error("Er ging iets mis bij het ophalen van de details:")
        st.code(e)

elif analysis_mode == "Teams":
    st.header("🛡️ Team Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")

elif analysis_mode == "Coaches":
    st.header("👔 Coach Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")
