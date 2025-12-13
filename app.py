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
    
    # Query voor dropdown vullen
    players_query = """
        SELECT p.commonname, p.id as "playerId", sq.name as "squadName"
        FROM public.players p
        JOIN analysis.final_impect_scores s ON p.id = CAST(s."playerId" AS TEXT)
        LEFT JOIN public.squads sq ON CAST(s."squadId" AS TEXT) = sq.id
        WHERE s."iterationId" = %s
        ORDER BY p.commonname;
    """
    
    try:
        p_iter_id = int(selected_iteration_id)
        df_players = run_query(players_query, params=(p_iter_id,))
        
        # Stap 1: Unieke namen
        unique_names = df_players['commonname'].unique().tolist()
        selected_player_name = st.sidebar.selectbox("Kies een speler:", unique_names)
        
        # Stap 2: Filteren
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

    # --- B. DATA OPHALEN OP BASIS VAN ID ---
    st.divider()
    
    # UPDATE: We halen nu ook BIO data op + Huidig Team
    # We joinen public.squads (alias sq_curr) op basis van p.currentSquadId
    score_query = """
        SELECT 
            p.commonname,
            a.position,
            p.birthdate,
            p.birthplace,
            p.leg,
            sq_curr.name as "current_team_name",
            
            -- KVK Hoofdscores
            a.cb_kvk_score, a.wb_kvk_score, a.dm_kvk_score,
            a.cm_kvk_score, a.acm_kvk_score, a.fa_kvk_score, a.fw_kvk_score,
            -- Sub-profielen
            a.footballing_cb_kvk_score, a.controlling_cb_kvk_score,
            a.defensive_wb_kvk_score, a.offensive_wingback_kvk_score,
            a.ball_winning_dm_kvk_score, a.playmaker_dm_kvk_score,
            a.box_to_box_cm_kvk_score, a.deep_running_acm_kvk_score,
            a.playmaker_off_acm_kvk_score, a.fa_inside_kvk_score,
            a.fa_wide_kvk_score, a.fw_target_kvk_score,
            a.fw_running_kvk_score, a.fw_finisher_kvk_score
        FROM analysis.final_impect_scores a
        JOIN public.players p ON CAST(a."playerId" AS TEXT) = p.id
        LEFT JOIN public.squads sq_curr ON p."currentSquadId" = sq_curr.id
        WHERE a."iterationId" = %s AND p.id = %s
    """
    
    try:
        p_iter_id = int(selected_iteration_id)
        p_player_id = str(final_player_id)
        
        df_scores = run_query(score_query, params=(p_iter_id, p_player_id))
        
        if not df_scores.empty:
            row = df_scores.iloc[0]
            
            # --- NIEUW: BIO DATA WEERGEVEN ---
            st.subheader(f"ℹ️ {selected_player_name}")
            
            # We gebruiken st.columns voor een mooie rij met info
            col_bio1, col_bio2, col_bio3, col_bio4 = st.columns(4)
            
            with col_bio1:
                st.metric("Huidig Team", row['current_team_name'] if row['current_team_name'] else "Onbekend")
            with col_bio2:
                # Datum netjes formatteren als tekst, of 'Onbekend' als leeg
                dob = str(row['birthdate']) if row['birthdate'] else "Onbekend"
                st.metric("Geboortedatum", dob)
            with col_bio3:
                st.metric("Geboorteplaats", row['birthplace'] if row['birthplace'] else "-")
            with col_bio4:
                # Voet checken
                foot = row['leg']
                if foot == 'right': foot = 'Rechts'
                elif foot == 'left': foot = 'Links'
                elif foot == 'both': foot = 'Tweebenig'
                st.metric("Voet", foot if foot else "-")
            
            st.markdown("---") # Een lijntje

            # --- VERDER MET DE PROFIELEN ---
            
            # COMPLETE Mapping
            profile_mapping = {
                "KVK Centrale Verdediger": row['cb_kvk_score'],
                "KVK Wingback": row['wb_kvk_score'],
                "KVK Verdedigende Mid.": row['dm_kvk_score'],
                "KVK Centrale Mid.": row['cm_kvk_score'],
                "KVK Aanvallende Mid.": row['acm_kvk_score'],
                "KVK Flank Aanvaller": row['fa_kvk_score'],
                "KVK Spits": row['fw_kvk_score'],
                
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
            
            active_profiles = {k: v for k, v in profile_mapping.items() if v is not None and v > 0}
            df_chart = pd.DataFrame(list(active_profiles.items()), columns=['Profiel', 'Score'])
            
            # Top Profiel Check
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

            # Visualisatie
            if top_profile_name:
                st.success(f"### ✅ Speler is POSITIEF op data profiel: {top_profile_name}")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
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
                    fig = px.pie(
                        df_chart, 
                        values='Score', 
                        names='Profiel', 
                        title=f'KVK Profielverdeling',
                        hole=0.4,
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
            st.error("Geen data gevonden voor deze speler ID.")

    except Exception as e:
        st.error("Er ging iets mis bij het ophalen van de details:")
        st.code(e)

elif analysis_mode == "Teams":
    st.header("🛡️ Team Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")

elif analysis_mode == "Coaches":
    st.header("👔 Coach Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")
