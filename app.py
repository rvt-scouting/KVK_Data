import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import numpy as np 

# -----------------------------------------------------------------------------
# 1. CONFIGURATIE & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="KVK Scouting", page_icon="🔴", layout="wide")
st.title("🔴⚪ KV Kortrijk - Data Scouting Platform")

# --- MAPPING: SPELER SCORES ---
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
        # ID is tekst
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

    # --- B. DATA OPHALEN ---
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
            
            # BIO
            st.subheader(f"ℹ️ {selected_player_name}")
            col_bio1, col_bio2, col_bio3, col_bio4 = st.columns(4)
            with col_bio1: st.metric("Huidig Team", row['current_team_name'] if row['current_team_name'] else "Onbekend")
            with col_bio2: st.metric("Geboortedatum", str(row['birthdate']) if row['birthdate'] else "-")
            with col_bio3: st.metric("Geboorteplaats", row['birthplace'] if row['birthplace'] else "-")
            with col_bio4: st.metric("Voet", row['leg'] if row['leg'] else "-")
            st.markdown("---")

            # PROFIELEN
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

            # METRIEKEN
            st.markdown("---")
            st.subheader("📊 Impect Speler Scores")
            metrics_config = get_config_for_position(row['position'], POSITION_METRICS)
            
            if metrics_config:
                def get_metrics_table(metric_ids):
                    if not metric_ids: return pd.DataFrame()
                    ids_tuple = tuple(str(x) for x in metric_ids)
                    m_query = """
                        SELECT d.name as "Metriek", d.details_label as "Detail", s.final_score_1_to_100 as "Score"
                        FROM analysis.player_final_scores s
                        JOIN public.player_score_definitions d ON CAST(s.metric_id AS TEXT) = d.id
                        WHERE s."iterationId" = %s AND s."playerId" = %s AND s.metric_id IN %s
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

            # KPIS
            st.markdown("---")
            st.subheader("📈 Impect Speler KPIs")
            kpis_config = get_config_for_position(row['position'], POSITION_KPIS)
            
            if kpis_config:
                def get_kpis_table(kpi_ids):
                    if not kpi_ids: return pd.DataFrame()
                    ids_tuple = tuple(str(x) for x in kpi_ids)
                    k_query = """
                        SELECT d.name as "KPI", d.context as "Context", s.final_score_1_to_100 as "Score"
                        FROM analysis.kpis_final_scores s
                        JOIN analysis.kpi_definitions d ON CAST(s.metric_id AS TEXT) = d.id
                        WHERE s."iterationId" = %s AND s."playerId" = %s AND s.metric_id IN %s
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

            # RAPPORTEN
            st.markdown("---")
            st.subheader("📑 Data Scout Rapporten")
            reports_query = """
                SELECT m."scheduledDate" as "Datum", sq_h.name as "Thuisploeg", sq_a.name as "Uitploeg", r.position as "Positie", r.label as "Verdict"
                FROM analysis.scouting_reports r
                JOIN public.matches m ON r."matchId" = m.id
                LEFT JOIN public.squads sq_h ON m."homeSquadId" = sq_h.id
                LEFT JOIN public.squads sq_a ON m."awaySquadId" = sq_a.id
                WHERE r."iterationId" = %s AND r."playerId" = %s AND m.available = true
                ORDER BY m."scheduledDate" DESC
            """
            try:
                df_reports = run_query(reports_query, params=(selected_iteration_id, p_player_id))
                if not df_reports.empty:
                    col_rep_table, col_rep_chart = st.columns([2, 1])
                    with col_rep_table: st.dataframe(df_reports, use_container_width=True, hide_index=True)
                    with col_rep_chart:
                        verdict_counts = df_reports['Verdict'].value_counts().reset_index()
                        verdict_counts.columns = ['Verdict', 'Aantal']
                        fig_verdict = px.pie(verdict_counts, values='Aantal', names='Verdict', title='Verdeling Verdicts', hole=0.4, color_discrete_sequence=['#d71920', '#bdc3c7', '#ecf0f1', '#c0392b'])
                        st.plotly_chart(fig_verdict, use_container_width=True)
                else: st.info("Geen data rapporten gevonden voor deze speler.")
            except Exception as e:
                st.error("Kon rapporten niet laden."); st.code(e)
            
            st.markdown("---")
            st.subheader("👀 Scout Rapporten")
            st.warning("🚧 Nog geen fysieke scouting rapporten beschikbaar.")

        else: st.error("Geen data gevonden voor deze speler ID.")
    except Exception as e: st.error("Er ging iets mis bij het ophalen van de details:"); st.code(e)

# ... (Bovenstaande code voor Scout Rapporten) ...

            # =========================================================
            # 7. VERGELIJKBARE SPELERS (SIMILARITY)
            # =========================================================
            st.markdown("---")
            st.subheader("👯 Vergelijkbare Spelers")
            
            # We halen alleen de actieve profielen van de huidige speler op om op te vergelijken
            # (Dus als het een spits is, vergelijken we niet op 'tackling')
            compare_columns = [col for col, score in profile_mapping.items() if score is not None and score > 0]
            
            # Mapping van de leesbare namen terug naar database kolomnamen
            # Dit is even nodig omdat profile_mapping de mooie namen gebruikt
            reverse_mapping = {
                "KVK Centrale Verdediger": 'cb_kvk_score', 
                "KVK Wingback": 'wb_kvk_score',
                "KVK Verdedigende Mid.": 'dm_kvk_score', 
                "KVK Centrale Mid.": 'cm_kvk_score',
                "KVK Aanvallende Mid.": 'acm_kvk_score', 
                "KVK Flank Aanvaller": 'fa_kvk_score',
                "KVK Spits": 'fw_kvk_score', 
                "Voetballende CV": 'footballing_cb_kvk_score',
                "Controlerende CV": 'controlling_cb_kvk_score', 
                "Verdedigende Back": 'defensive_wb_kvk_score',
                "Aanvallende Back": 'offensive_wingback_kvk_score', 
                "Ballenafpakker (CVM)": 'ball_winning_dm_kvk_score',
                "Spelmaker (CVM)": 'playmaker_dm_kvk_score', 
                "Box-to-Box (CM)": 'box_to_box_cm_kvk_score',
                "Diepgaande '10'": 'deep_running_acm_kvk_score', 
                "Spelmakende '10'": 'playmaker_off_acm_kvk_score',
                "Buitenspeler (Binnendoor)": 'fa_inside_kvk_score', 
                "Buitenspeler (Buitenom)": 'fa_wide_kvk_score',
                "Targetman": 'fw_target_kvk_score', 
                "Lopende Spits": 'fw_running_kvk_score',
                "Afmaker": 'fw_finisher_kvk_score'
            }
            
            db_columns_to_compare = [reverse_mapping[c] for c in compare_columns if c in reverse_mapping]

            if db_columns_to_compare:
                with st.expander(f"Toon top 10 spelers die lijken op {selected_player_name}", expanded=False):
                    
                    st.caption(f"Vergelijking gebaseerd op positie '{row['position']}' en {len(db_columns_to_compare)} actieve profielen.")
                    
                    # 1. Haal data op van ALLE spelers met DEZELFDE positie uit ALLE seizoenen
                    # We moeten dynamisch de kolommen opbouwen voor de query
                    cols_string = ", ".join([f'a.{c}' for c in db_columns_to_compare])
                    
                    sim_query = f"""
                        SELECT 
                            p.id as "playerId", 
                            p.commonname as "Naam", 
                            sq.name as "Team", 
                            i.season as "Seizoen",
                            {cols_string}
                        FROM analysis.final_impect_scores a
                        JOIN public.players p ON a."playerId" = p.id
                        LEFT JOIN public.squads sq ON a."squadId" = sq.id
                        JOIN public.iterations i ON a."iterationId" = i.id
                        WHERE a.position = %s
                    """
                    
                    try:
                        df_all_players = run_query(sim_query, params=(row['position'],))
                        
                        if not df_all_players.empty:
                            # Zorg dat playerId uniek is per rij voor de berekening (combinatie ID + Seizoen is uniek)
                            # We maken een unieke index
                            df_all_players['unique_id'] = df_all_players['playerId'].astype(str) + "_" + df_all_players['Seizoen']
                            df_calculation = df_all_players.set_index('unique_id')
                            
                            # De geselecteerde speler (Target)
                            current_unique_id = f"{p_player_id}_{selected_season}"
                            
                            if current_unique_id in df_calculation.index:
                                # We nemen de target vector (alleen de score kolommen)
                                target_vector = df_calculation.loc[current_unique_id, db_columns_to_compare]
                                
                                # De rest van de data (alleen de score kolommen)
                                others_vectors = df_calculation[db_columns_to_compare]
                                
                                # 2. Bereken verschil (Mean Absolute Difference)
                                # Hoe lager het verschil, hoe hoger de gelijkenis
                                diff = (others_vectors - target_vector).abs().mean(axis=1)
                                similarity = 100 - diff
                                
                                # 3. Top 10 (jezelf uitsluiten)
                                similarity = similarity.sort_values(ascending=False)
                                similarity = similarity[similarity.index != current_unique_id]
                                
                                top_10_ids = similarity.head(10).index
                                
                                # 4. De data weer ophalen voor de tabel weergave
                                results = df_calculation.loc[top_10_ids].copy()
                                results['Gelijkenis %'] = similarity.loc[top_10_ids]
                                
                                # Mooie tabel maken
                                display_cols = ['Naam', 'Team', 'Seizoen', 'Gelijkenis %']
                                
                                # Kleurfunctie (hergebruikt)
                                def color_similarity(val):
                                    color = '#2ecc71' if val > 90 else '#27ae60' if val > 80 else 'black'
                                    weight = 'bold' if val > 80 else 'normal'
                                    return f'color: {color}; font-weight: {weight}'

                                st.dataframe(
                                    results[display_cols]
                                    .style.applymap(color_similarity, subset=['Gelijkenis %'])
                                    .format({'Gelijkenis %': '{:.1f}%'}),
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                            else:
                                st.warning("Kon de huidige speler niet vinden in de vergelijkingsset.")
                        else:
                            st.info("Geen andere spelers gevonden met deze positie om mee te vergelijken.")
                            
                    except Exception as e:
                        st.error("Fout bij berekenen similarity.")
                        st.code(e)
            else:
                st.info("Deze speler heeft geen actieve profielscores om op te vergelijken.")

# === MODUS: TEAMS ===
elif analysis_mode == "Teams":
    st.header("🛡️ Team Analyse")
    
    # --- A. TEAM SELECTIE ---
    st.sidebar.header("3. Team Selectie")
    
    # We halen teams op die data hebben
    teams_query = """
        SELECT DISTINCT sq.name, sq.id as "squadId"
        FROM public.squads sq
        JOIN analysis.squad_final_scores s ON sq.id = s."squadId"
        WHERE s."iterationId" = %s
        ORDER BY sq.name;
    """
    
    try:
        df_teams = run_query(teams_query, params=(selected_iteration_id,))
        
        team_names = df_teams['name'].tolist()
        selected_team_name = st.sidebar.selectbox("Kies een team:", team_names)
        
        candidate_rows = df_teams[df_teams['name'] == selected_team_name]
        
        final_squad_id = None
        
        if len(candidate_rows) > 1:
            st.sidebar.warning(f"⚠️ Meerdere teams gevonden met naam '{selected_team_name}'.")
            squad_options = candidate_rows.apply(lambda x: f"{x['name']} (ID: {x['squadId']})", axis=1).tolist()
            selected_option = st.sidebar.selectbox("Specifieer team:", squad_options)
            
            selected_id_str = selected_option.split("ID: ")[1].replace(")", "")
            final_squad_id = selected_id_str
            
        elif len(candidate_rows) == 1:
            final_squad_id = candidate_rows.iloc[0]['squadId']
            
        else:
            st.error("Geen team gevonden.")
            st.stop()
            
        # --- B. HOOFDSCHERM TEAM ---
        if final_squad_id:
            st.divider()
            
            team_details_query = """
                SELECT name, "imageUrl"
                FROM public.squads
                WHERE id = %s
            """
            df_team_details = run_query(team_details_query, params=(final_squad_id,))
            
            if not df_team_details.empty:
                team_row = df_team_details.iloc[0]
                team_name_display = team_row['name']
                team_logo_url = team_row['imageUrl']
                
                # Layout met logo
                col_logo, col_name = st.columns([1, 5])
                
                with col_logo:
                    if team_logo_url:
                        st.image(team_logo_url, width=100)
                
                with col_name:
                    st.header(f"🛡️ {team_name_display}")
                    
                # --- TEAM PROFIELEN ---
                st.divider()
                st.subheader("📊 Team Profiel Scores")
                
                squad_profile_query = """
                    SELECT profile_name as "Profiel", score as "Score"
                    FROM analysis.squad_profile_scores
                    WHERE "squadId" = %s AND "iterationId" = %s
                    ORDER BY score DESC;
                """
                
                try:
                    df_profiles = run_query(squad_profile_query, params=(final_squad_id, selected_iteration_id))
                    
                    if not df_profiles.empty:
                        col_prof_table, col_prof_chart = st.columns([1, 2])
                        
                        def highlight_high_scores(val):
                            if isinstance(val, (int, float)) and val > 66: return 'color: #2ecc71; font-weight: bold'
                            return ''

                        with col_prof_table:
                            st.dataframe(
                                df_profiles.style.applymap(highlight_high_scores, subset=['Score']).format({'Score': '{:.1f}'}),
                                use_container_width=True,
                                hide_index=True
                            )
                            
                        with col_prof_chart:
                            fig_profiles = px.bar(
                                df_profiles, 
                                x='Profiel', 
                                y='Score',
                                title="Score per Profiel",
                                color_discrete_sequence=['#d71920']
                            )
                            st.plotly_chart(fig_profiles, use_container_width=True)
                            
                    else:
                        st.info("Geen profielscores gevonden voor dit team.")
                        
                except Exception as e:
                    st.error("Fout bij ophalen team profielen.")
                    st.code(e)
                
                # Styling functie voor Inverted cellen
                def highlight_inverted(val):
                    if str(val).lower().strip() == 'true':
                        return 'background-color: #e74c3c; color: white; font-weight: bold'
                    return ''

                # --- 1. TEAM SCORES (Metrieken) - Uitklapbaar ---
                with st.expander("📊 Team Impect Scores (Metrieken)", expanded=False):
                    
                    score_team_query = """
                        SELECT 
                            d.name as "Metriek",
                            d.details_label as "Detail",
                            d.inverted as "Inverted",
                            s.final_score_1_to_100 as "Score"
                        FROM analysis.squad_final_scores s
                        JOIN public.squad_score_definitions d ON d.id = REPLACE(s.metric_id, 's', '')
                        WHERE s."squadId" = %s AND s."iterationId" = %s
                        ORDER BY s.final_score_1_to_100 DESC
                    """
                    
                    try:
                        df_team_scores = run_query(score_team_query, params=(final_squad_id, selected_iteration_id))
                        
                        if not df_team_scores.empty:
                            st.dataframe(
                                df_team_scores.style
                                    .applymap(highlight_high_scores, subset=['Score'])
                                    .applymap(highlight_inverted, subset=['Inverted'])
                                    .format({'Score': '{:.1f}'}),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("Geen team metrieken gevonden.")
                    except Exception as e:
                        st.error("Fout bij ophalen team scores.")
                        st.code(e)


                # --- 2. TEAM KPIs (Details) - Uitklapbaar ---
                with st.expander("📉 Team Impect KPIs (Details)", expanded=False):
                    
                    # FIX: Geen d.inverted in SELECT
                    kpi_query = """
                        SELECT 
                            d.name as "KPI",
                            s.final_score_1_to_100 as "Score"
                        FROM analysis.squadkpi_final_scores s
                        JOIN analysis.kpi_definitions d ON d.id = REPLACE(s.metric_id, 'k', '')
                        WHERE s."squadId" = %s AND s."iterationId" = %s
                        ORDER BY s.final_score_1_to_100 DESC
                    """
                    
                    try:
                        df_kpis = run_query(kpi_query, params=(final_squad_id, selected_iteration_id))
                        
                        if not df_kpis.empty:
                            # FIX: Geen highlight_inverted in style
                            st.dataframe(
                                df_kpis.style
                                    .applymap(highlight_high_scores, subset=['Score'])
                                    .format({'Score': '{:.1f}'}),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("Geen KPI data gevonden.")
                            
                    except Exception as e:
                        st.error("Fout bij ophalen Team KPIs")
                        st.code(e)

                # --- 3. VERGELIJKBARE TEAMS (SIMILARITY) ---
                st.markdown("---")
                st.subheader("🤝 Vergelijkbare Teams")
                st.caption("Gebaseerd op de 4 profielscores over alle seizoenen.")

                all_profiles_query = """
                    SELECT s."squadId", sq.name as "Team", i.season as "Seizoen", s.profile_name, s.score
                    FROM analysis.squad_profile_scores s
                    JOIN public.squads sq ON s."squadId" = sq.id
                    JOIN public.iterations i ON s."iterationId" = i.id
                """
                
                try:
                    df_all_profiles = run_query(all_profiles_query)
                    
                    if not df_all_profiles.empty:
                        df_pivot = df_all_profiles.pivot_table(
                            index=['squadId', 'Team', 'Seizoen'], 
                            columns='profile_name', 
                            values='score'
                        ).fillna(0)
                        
                        current_season_name = selected_season
                        
                        if (final_squad_id, team_name_display, current_season_name) in df_pivot.index:
                            target_vector = df_pivot.loc[(final_squad_id, team_name_display, current_season_name)]
                            diff = (df_pivot - target_vector).abs().mean(axis=1)
                            similarity = 100 - diff
                            
                            similarity = similarity.sort_values(ascending=False)
                            similarity = similarity[similarity.index != (final_squad_id, team_name_display, current_season_name)]
                            
                            top_5 = similarity.head(5).reset_index()
                            top_5.columns = ['ID', 'Team', 'Seizoen', 'Gelijkenis %']
                            
                            # FIX: Kleurfunctie zonder Matplotlib
                            def color_similarity(val):
                                # Donkergroen > 90, Lichtgroen > 80, anders standaard
                                color = '#2ecc71' if val > 90 else '#27ae60' if val > 80 else 'black'
                                weight = 'bold' if val > 80 else 'normal'
                                return f'color: {color}; font-weight: {weight}'

                            st.dataframe(
                                top_5[['Team', 'Seizoen', 'Gelijkenis %']]
                                .style.applymap(color_similarity, subset=['Gelijkenis %'])
                                .format({'Gelijkenis %': '{:.1f}%'}),
                                use_container_width=True,
                                hide_index=True
                            )
                            
                        else:
                            st.warning("Kon de vector voor dit team niet vinden in de dataset voor vergelijking.")
                            
                    else:
                        st.error("Kon geen referentiedata ophalen voor vergelijking.")

                except Exception as e:
                    st.error("Fout bij berekenen vergelijkbare teams.")
                    st.code(e)
                
            else:
                st.error("Kon team details niet ophalen.")

    except Exception as e:
        st.error("Kon teamlijst niet ophalen.")
        st.code(e)


elif analysis_mode == "Coaches":
    st.header("👔 Coach Analyse")
    st.warning("🚧 Aan deze module wordt nog gewerkt.")
