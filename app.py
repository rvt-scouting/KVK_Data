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
    
    # UPDATE: Nu halen we ECHT alle kolommen op, inclusief de KVK hoofdscores
    score_query = """
        SELECT 
            p.commonname,
            a.position,
            -- KVK Hoofdscores (De belangrijkste!)
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
        WHERE a."iterationId" = %s AND p.commonname = %s
    """
    
    try:
        df_scores = run_query(score_query, params=(selected_iteration_id, selected_player))
        
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
                "Diepgaande '10'": row['deep_running_acm_kvk_score'],
                "Spelmakende '10'": row['playmaker_off_acm_kvk_score'],
                "Buitenspeler (Binnendoor)": row['fa_inside_kvk_score'],
                "Buitenspeler (Buitenom)": row['fa_wide_kvk_score'],
                "Targetman": row['fw_target_kvk_score'],
                "Lopende Spits": row['fw_running_kvk_score'],
                "Afmaker": row['fw_finisher_kvk_score']
            }
            
            # Filteren: alleen profielen met een score tonen
            active_profiles = {k: v for k, v in profile_mapping.items() if v is not None and v > 0}
            df_chart = pd.DataFrame(list(active_profiles.items()), columns=['Profiel', 'Score'])
            
            # --- C. BEREKENINGEN ---
            
            top_profile_name = None
            
            if not df_chart.empty:
                df_chart = df_chart.sort_values(by='Score', ascending=False)
                highest_row = df_chart.iloc[0]
                if highest_row['Score'] > 66:
                    top_profile_name = highest_row['Profiel']

            def highlight_high_scores(val):
                if isinstance(val, (int, float)) and val > 66:
                    return 'color: #2ecc71; font-weight: bold'
                return ''

            # --- D. WEERGAVE ---
            
            if top_profile_name:
                st.success(f"### ✅ Speler is POSITIEF op data profiel: {top_profile_name}")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader(f"{selected_player}")
                st.write(f"**Positie:** {row['position']}")
                st.write("Score per profiel:")
                
                st.dataframe(
                    df_chart.style.applymap(highlight_high_scores, subset=['Score'])
                            .format({'Score': '{:.1f}'}),
                    use_container_width=True,
                    hide_index=True
                )
                
            with col2:
                if not df_chart.empty:
                    # De Pie Chart
                    fig = px.pie(
                        df_chart, 
                        values='Score', 
                        names='Profiel', 
                        title=f'KVK Profielverdeling',
                        hole=0.4,
                        # KVK Kleuren: Rood tinten en grijs/wit
                        color_discrete_sequence=['#d71920', '#ecf0f1', '#bdc3c7', '#c0392b'] 
                    )
                    
                    fig.update_traces(
                        textinfo='value', 
                        textfont_size=15,
                        marker=dict(line=dict(color='#000000', width=1))
                    )
                    
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
