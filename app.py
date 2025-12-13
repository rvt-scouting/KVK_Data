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

# --- MAPPING: SPELER KPIS ---
POSITION_KPIS = {
    "central_defender": {
        "aan_bal": [107, 106, 1534, 21, 2, 0, 1405, 1422],
        "zonder_bal": [1016, 1015, 1014, 24, 867, 1409]
    },
    "wingback": {
        "aan_bal": [172, 171, 2, 9, 0],
        "zonder_bal": [23, 27, 1409, 1536, 1523]
    },
    "defensive_midfield": {
        "aan_bal": [184, 0, 107, 87, 106, 109, 122, 1422, 1423],
        "zonder_bal": [21, 23, 27, 865, 867, 619, 1536, 1610]
    },
    "central_midfield": {
        "aan_bal": [0, 1405, 1425],
        "zonder_bal": [23, 27, 24, 1536]
    },
    "attacking_midfield": {
        "aan_bal": [77, 1350, 2, 169, 167, 467, 0, 7, 141, 1425, 1422, 1423, 1253, 1252, 1254],
        "zonder_bal": [1536]
    },
    "winger": {
        "aan_bal": [25, 2, 88, 172, 171, 167, 9, 87, 7, 1401, 1425],
        "zonder_bal": [1536]
    },
    "center_forward": {
        "aan_bal": [9, 427, 426, 1401, 82],
        "zonder_bal": [1536]
    }
}

def get_config_for_position(db_position, config_dict):
    if not db_position:
        return None
    
    pos = str(db_position).upper().strip()
    
    if pos == "CENTRAL_DEFENDER":
        return config_dict.get('central_defender')
    elif pos in ["RIGHT_WINGBACK_DEFENDER", "LEFT_WINGBACK_DEFENDER"]:
        return config_dict.get('wingback')
    elif pos in ["DEFENSIVE_MIDFIELD", "DEFENSE_MIDFIELD"]:
        return config_dict.get('defensive_midfield')
    elif pos == "CENTRAL_MIDFIELD":
        return config_dict.get('central_midfield')
    elif pos in ["ATTACKING_MIDFIELD", "OFFENSIVE_MIDFIELD"]:
        return config_dict.get('attacking_midfield')
    elif pos in ["RIGHT_WINGER", "LEFT_WINGER"]:
        return config_dict.get('winger')
    elif pos in ["CENTER_FORWARD", "STRIKER"]:
        return config_dict.get('center_forward')
    
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
    
    players_query = """
        SELECT p.commonname, p.id as "playerId", sq.name as "squadName"
        FROM public.players p
        JOIN analysis.final_impect_scores s ON p.id = s."playerId"
        LEFT JOIN public.squads sq ON s."squadId" = sq.id
        WHERE s."iterationId" = %s
        ORDER BY p.commonname;
    """
    
    try:
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
        p_player_id = str(final_player_id)
        
        df_scores = run_query(score_query, params=(selected_iteration_id, p_player_id))
        
        if not df_scores.empty:
            row = df_scores.iloc[0]
            
            # 1. BIO
            st.subheader(f"ℹ️ {selected_player_name}")
            col_bio1, col_bio2, col_bio3, col_bio4 = st.columns(4)
            with col_bio1: st.metric("Huidig Team", row['current_team_name'] if row['current_team_name'] else "Onbekend")
            with col_bio2: st.metric("Geboortedatum", str(row['birthdate']) if row['birthdate'] else "-")
            with col_bio3: st.metric("Geboorteplaats", row['birthplace'] if row['birthplace'] else "-")
            with col_bio4: st.metric("Voet", row['leg'] if row['leg'] else "-")
            st.markdown("---")

            # 2. PROFIEL SCORE (Taart)
            profile_mapping = {
                "KVK Centrale Verdediger": row['cb_kvk_score'], "KVK Wingback": row['wb_kvk_score'],
                "KVK Verdedigende Mid.": row['dm_kvk_score'], "KVK Centrale Mid.": row['cm_kvk_score'],
                "KVK Aanvallende Mid.": row['acm_kvk_score'], "KVK Flank Aanvaller": row['fa_kvk_score'],
                "KVK Spits": row['fw_kvk_score'], "Voetballende CV": row['footballing_cb_kvk_score'],
                "Controlerende CV": row['controlling_cb_kvk_score'], "Verdedigende Back": row['defensive_wb_kvk_score'],
                "Aanvallende Back": row['offensive_wingback_kvk_score'], "Ballenafpakker (CVM)": row['ball_winning_dm_kvk_score'],
                "Spelmaker (CVM)": row['playmaker_dm_kvk_score'], "Box-to-Box (CM)": row['box_to_box_cm_kvk_score'],
                "Diepgaande '10'": row['deep_running_acm_kvk_score'], "Spelmakende '10'": row['playmaker_off_acm_kvk_score'],
                "Buitenspeler (Binnendoor)": row['fa_inside_kvk_score'], "Buitenspeler (Buitenom)": row['fa_wide_kvk_score'],
                "Targetman": row['fw_target_kvk_score'], "Lopende Spits": row['fw_running_kvk_score'],
                "Afmaker": row['fw_finisher_kvk_score']
            }
            active_profiles = {k: v for k, v in profile_mapping.items() if v is not None and v > 0}
            df_chart = pd.DataFrame(list(active_profiles.items()), columns=['Profiel', 'Score'])
            
            top_profile_name = None
            if not df_chart.empty:
                df_chart = df_chart.sort_values(by='Score', ascending=False)
                if df_chart.iloc[0]['Score'] > 66: top_profile_name = df_chart.iloc[0]['Profiel']

            def highlight_high_scores(val):
                if isinstance(val, (int, float)) and val > 66: return 'color: #2ecc71; font-weight: bold'
                return ''

            if top_profile_name: st.success(f"### ✅ Speler is POSITIEF op data profiel: {top_profile_name}")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.write(f"**Positie:** {row['position']}")
                st.dataframe(df_chart.style.applymap(highlight_high_scores, subset=['Score']).format({'Score': '{:.1f}'}), use_container_width=True, hide_index=True)
            with c2:
                if not df_chart.empty:
                    fig = px.pie(df_chart, values='Score', names='Profiel', title=f'KVK Profielverdeling', hole=0.4, color_discrete_sequence=['#d71920', '#ecf0f1', '#bdc3c7', '#c0392b'])
                    fig.update_traces(textinfo='value', textfont_size=15, marker=dict(line=dict(color='#000000', width=1)))
                    st.plotly_chart(fig, use_container_width=True)


            # =========================================================
            # 3. SPECIFIEKE METRIEKEN (PIRAMIDE LAAG 2)
            # =========================================================
            st.markdown("---")
            st.subheader("📊 Impect Speler Scores")
            
            metrics_config = get_config_for_position(row['position'], POSITION_METRICS)
            
            if metrics_config:
                def get_metrics_table(metric_ids):
                    if not metric_ids: return pd.DataFrame()
                    ids_tuple = tuple(str(x) for x in metric_ids)
                    m_query = """
                        SELECT 
                            d.name as "Metriek",
                            d.details_label as "Detail", 
                            s.final_score_1_to_100 as "Score"
                        FROM analysis.player_final_scores s
                        JOIN public.player_score_definitions d ON CAST(s.metric_id AS TEXT) = d.id
                        WHERE s."iterationId" = %s
                          AND s."playerId" = %s
                          AND s.metric_id IN %s
                        ORDER BY s.final_score_1_to_100 DESC
                    """
                    return run_query(m_query, params=(selected_iteration_id, p_player_id, ids_tuple))

                df_aan_bal = get_metrics_table(metrics_config.get('aan_bal', []))
                df_zonder_bal = get_metrics_table(metrics_config.get('zonder_bal', []))
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.write("⚽ **Aan de Bal**")
                    if not df_aan_bal.empty: st.dataframe(df_aan_bal.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
                    else: st.caption("Geen data.")
                with col_m2:
                    st.write("🛡️ **Zonder Bal / Defensief**")
                    if not df_zonder_bal.empty: st.dataframe(df_zonder_bal.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
                    else: st.caption("Geen data.")     
            else:
                st.info(f"Geen metrieken gevonden voor positie: '{row['position']}'")


            # =========================================================
            # 4. IMPECT KPIS (PIRAMIDE LAAG 3)
            # =========================================================
            st.markdown("---")
            st.subheader("📈 Impect Speler KPIs")
            
            kpis_config = get_config_for_position(row['position'], POSITION_KPIS)
            
            if kpis_config:
                def get_kpis_table(kpi_ids):
                    if not kpi_ids: return pd.DataFrame()
                    ids_tuple = tuple(str(x) for x in kpi_ids)
                    k_query = """
                        SELECT 
                            d.name as "KPI",
                            d.context as "Context", 
                            s.final_score_1_to_100 as "Score"
                        FROM analysis.kpis_final_scores s
                        JOIN analysis.kpi_definitions d ON CAST(s.metric_id AS TEXT) = d.id
                        WHERE s."iterationId" = %s
                          AND s."playerId" = %s
                          AND s.metric_id IN %s
                        ORDER BY s.final_score_1_to_100 DESC
                    """
                    return run_query(k_query, params=(selected_iteration_id, p_player_id, ids_tuple))

                df_kpi_aan_bal = get_kpis_table(kpis_config.get('aan_bal', []))
                df_kpi_zonder_bal = get_kpis_table(kpis_config.get('zonder_bal', []))
                
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    st.write("⚽ **Aan de Bal (KPIs)**")
                    if not df_kpi_aan_bal.empty: st.dataframe(df_kpi_aan_bal.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
                    else: st.caption("Geen KPI data.")
                with col_k2:
                    st.write("🛡️ **Zonder Bal / Defensief (KPIs)**")
                    if not df_kpi_zonder_bal.empty: st.dataframe(df_kpi_zonder_bal.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
                    else: st.caption("Geen KPI data.")     
            else:
                st.info(f"Geen KPIs gevonden voor positie: '{row['position']}'")

            # =========================================================
            # 5. KWALITEITEN & WERKPUNTEN (PLACEHOLDER)
            # =========================================================
            st.markdown("---")
            st.subheader("⚖️ Kwaliteiten & Werkpunten")
            st.info("🚧 Hier komen de sterke en zwakke punten van de speler (gegenereerd of handmatig).")

            # =========================================================
            # 6. RAPPORTEN (PLACEHOLDERS)
            # =========================================================
            st.markdown("---")
            col_rep1, col_rep2 = st.columns(2)
            
            with col_rep1:
                st.subheader("📑 Data Scout Rapporten")
                st.warning("🚧 Nog geen data rapporten beschikbaar.")
                
            with col_rep2:
                st.subheader("👀 Scout Rapporten")
                st.warning("🚧 Nog geen fysieke scouting rapporten beschikbaar.")


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
