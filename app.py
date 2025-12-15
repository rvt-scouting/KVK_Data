import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import numpy as np

# -----------------------------------------------------------------------------
# 0. NAVIGATIE LOGICA (MOET HELEMAAL BOVENAAN STAAN)
# -----------------------------------------------------------------------------
if "pending_nav" in st.session_state:
    nav = st.session_state.pending_nav
    try:
        st.session_state.sb_season = nav["season"]
        st.session_state.sb_competition = nav["competition"]
        if nav["mode"] == "Spelers":
            st.session_state.sb_player = nav["target_name"]
        elif nav["mode"] == "Teams":
            st.session_state.sb_team = nav["target_name"]
    except Exception as e:
        print(f"Navigatie fout: {e}")
    del st.session_state.pending_nav

# -----------------------------------------------------------------------------
# 1. CONFIGURATIE & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="KVK Scouting", page_icon="🔴", layout="wide")
st.title("🔴⚪ KV Kortrijk - Data Scouting Platform")

# --- MAPPING: SPELER SCORES ---
POSITION_METRICS = {
    "central_defender": {"aan_bal": [66, 58, 64, 10, 163], "zonder_bal": [103, 93, 32, 94, 17, 65, 92]},
    "wingback": {"aan_bal": [61, 66, 58, 54, 53, 52, 10, 9, 14], "zonder_bal": [68, 69, 17, 70]},
    "defensive_midfield": {"aan_bal": [60, 10, 163, 44], "zonder_bal": [29, 65, 17, 16, 69, 68, 67]},
    "central_midfield": {"aan_bal": [60, 61, 62, 73, 72, 64, 10, 163, 145], "zonder_bal": [65, 17, 69, 68]},
    "attacking_midfield": {"aan_bal": [60, 61, 62, 73, 58, 2, 15, 52, 72, 10, 74, 9], "zonder_bal": []},
    "winger": {"aan_bal": [60, 61, 62, 58, 54, 1, 53, 10, 9, 14, 6, 145], "zonder_bal": []},
    "center_forward": {"aan_bal": [60, 61, 62, 73, 63, 2, 64, 10, 74, 9, 92, 97, 14, 6, 145], "zonder_bal": []}
}

# --- MAPPING: SPELER KPIS ---
POSITION_KPIS = {
    "central_defender": {"aan_bal": [107, 106, 1534, 21, 2, 0, 1405, 1422], "zonder_bal": [1016, 1015, 1014, 24, 867, 1409]},
    "wingback": {"aan_bal": [172, 171, 2, 9, 0], "zonder_bal": [23, 27, 1409, 1536, 1523]},
    "defensive_midfield": {"aan_bal": [184, 0, 107, 87, 106, 109, 122, 1422, 1423], "zonder_bal": [21, 23, 27, 865, 867, 619, 1536, 1610]},
    "central_midfield": {"aan_bal": [0, 1405, 1425], "zonder_bal": [23, 27, 24, 1536]},
    "attacking_midfield": {"aan_bal": [77, 1350, 2, 169, 167, 467, 0, 7, 141, 1425, 1422, 1423, 1253, 1252, 1254], "zonder_bal": [1536]},
    "winger": {"aan_bal": [25, 2, 88, 172, 171, 167, 9, 87, 7, 1401, 1425], "zonder_bal": [1536]},
    "center_forward": {"aan_bal": [9, 427, 426, 1401, 82], "zonder_bal": [1536]}
}

def get_config_for_position(db_position, config_dict):
    if not db_position: return None
    pos = str(db_position).upper().strip()
    if pos == "CENTRAL_DEFENDER": return config_dict.get('central_defender')
    elif pos in ["RIGHT_WINGBACK_DEFENDER", "LEFT_WINGBACK_DEFENDER"]: return config_dict.get('wingback')
    elif pos in ["DEFENSIVE_MIDFIELD", "DEFENSE_MIDFIELD"]: return config_dict.get('defensive_midfield')
    elif pos == "CENTRAL_MIDFIELD": return config_dict.get('central_midfield')
    elif pos in ["ATTACKING_MIDFIELD", "OFFENSIVE_MIDFIELD"]: return config_dict.get('attacking_midfield')
    elif pos in ["RIGHT_WINGER", "LEFT_WINGER"]: return config_dict.get('winger')
    elif pos in ["CENTER_FORWARD", "STRIKER"]: return config_dict.get('center_forward')
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

# --- PERFORMANCE UPDATE: CACHING ---
# ttl=3600 zorgt dat de data 1 uur in het geheugen blijft.
@st.cache_data(ttl=3600)
def run_query(query, params=None):
    conn = init_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# 2. SIDEBAR FILTERS
# -----------------------------------------------------------------------------
st.sidebar.header("1. Selecteer Data")

season_query = "SELECT DISTINCT season FROM public.iterations ORDER BY season DESC;"
try:
    df_seasons = run_query(season_query)
    seasons_list = df_seasons['season'].tolist()
    selected_season = st.sidebar.selectbox("Seizoen:", seasons_list, key="sb_season")
except Exception as e:
    st.error("Kon seizoenen niet laden."); st.stop()

if selected_season:
    competition_query = 'SELECT DISTINCT "competitionName" FROM public.iterations WHERE season = %s ORDER BY "competitionName";'
    df_competitions = run_query(competition_query, params=(selected_season,))
    competitions_list = df_competitions['competitionName'].tolist()
    selected_competition = st.sidebar.selectbox("Competitie:", competitions_list, key="sb_competition")
else: selected_competition = None

st.sidebar.divider() 

# -----------------------------------------------------------------------------
# 3. ANALYSE MODUS
# -----------------------------------------------------------------------------
st.sidebar.header("2. Analyse Niveau")
analysis_mode = st.sidebar.radio("Wat wil je analyseren?", ["Spelers", "Teams", "Coaches"])

selected_iteration_id = None
if selected_season and selected_competition:
    details_query = 'SELECT season, "competitionName", id FROM public.iterations WHERE season = %s AND "competitionName" = %s LIMIT 1;'
    df_details = run_query(details_query, params=(selected_season, selected_competition))
    if not df_details.empty:
        selected_iteration_id = str(df_details.iloc[0]['id'])
        st.info(f"Je kijkt nu naar: **{selected_competition}** ({selected_season})")
    else: st.error("Kon geen ID vinden."); st.stop() 
else: st.warning("👈 Kies eerst een seizoen en competitie."); st.stop() 

# -----------------------------------------------------------------------------
# 5. HOOFDSCHERM LOGICA
# -----------------------------------------------------------------------------

# =============================================================================
# A. SPELERS MODUS
# =============================================================================
if analysis_mode == "Spelers":
    st.header("🏃‍♂️ Speler Analyse")
    
    # 1. SPELER SELECTIE
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
        selected_player_name = st.sidebar.selectbox("Kies een speler:", unique_names, key="sb_player")
        
        candidate_rows = df_players[df_players['commonname'] == selected_player_name]
        final_player_id = None
        
        if len(candidate_rows) > 1:
            st.sidebar.warning(f"⚠️ Meerdere spelers gevonden: '{selected_player_name}'.")
            squad_options = [s for s in candidate_rows['squadName'].tolist() if s is not None]
            if squad_options:
                selected_squad = st.sidebar.selectbox("Kies team:", squad_options)
                final_player_id = candidate_rows[candidate_rows['squadName'] == selected_squad].iloc[0]['playerId']
            else: final_player_id = candidate_rows.iloc[0]['playerId']
        elif len(candidate_rows) == 1: final_player_id = candidate_rows.iloc[0]['playerId']
        else: st.error("Selectie fout."); st.stop()
    except Exception as e: st.error("Fout bij ophalen spelers."); st.code(e); st.stop()

    # 2. DATA OPHALEN
    st.divider()
    score_query = """
        SELECT p.commonname, a.position, p.birthdate, p.birthplace, p.leg, sq_curr.name as "current_team_name",
            a.cb_kvk_score, a.wb_kvk_score, a.dm_kvk_score, a.cm_kvk_score, a.acm_kvk_score, a.fa_kvk_score, a.fw_kvk_score,
            a.footballing_cb_kvk_score, a.controlling_cb_kvk_score, a.defensive_wb_kvk_score, a.offensive_wingback_kvk_score,
            a.ball_winning_dm_kvk_score, a.playmaker_dm_kvk_score, a.box_to_box_cm_kvk_score, a.deep_running_acm_kvk_score,
            a.playmaker_off_acm_kvk_score, a.fa_inside_kvk_score, a.fa_wide_kvk_score, a.fw_target_kvk_score,
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
            st.subheader(f"ℹ️ {selected_player_name}")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Huidig Team", row['current_team_name'] or "Onbekend")
            with c2: st.metric("Geboortedatum", str(row['birthdate']) or "-")
            with c3: st.metric("Geboorteplaats", row['birthplace'] or "-")
            with c4: st.metric("Voet", row['leg'] or "-")
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
                "Targetman": row['fw_target_kvk_score'], "Lopende Spits": row['fw_running_kvk_score'], "Afmaker": row['fw_finisher_kvk_score']
            }
            active_profiles = {k: v for k, v in profile_mapping.items() if v is not None and v > 0}
            df_chart = pd.DataFrame(list(active_profiles.items()), columns=['Profiel', 'Score'])
            
            def highlight_high_scores(val):
                return 'color: #2ecc71; font-weight: bold' if isinstance(val, (int, float)) and val > 66 else ''

            top_profile_name = df_chart.sort_values(by='Score', ascending=False).iloc[0]['Profiel'] if not df_chart.empty and df_chart.iloc[0]['Score'] > 66 else None
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
            st.markdown("---"); st.subheader("📊 Impect Speler Scores")
            metrics_config = get_config_for_position(row['position'], POSITION_METRICS)
            if metrics_config:
                def get_metrics_table(metric_ids):
                    if not metric_ids: return pd.DataFrame()
                    ids_tuple = tuple(str(x) for x in metric_ids)
                    q = """SELECT d.name as "Metriek", d.details_label as "Detail", s.final_score_1_to_100 as "Score" FROM analysis.player_final_scores s JOIN public.player_score_definitions d ON CAST(s.metric_id AS TEXT) = d.id WHERE s."iterationId" = %s AND s."playerId" = %s AND s.metric_id IN %s ORDER BY s.final_score_1_to_100 DESC"""
                    return run_query(q, params=(selected_iteration_id, p_player_id, ids_tuple))
                df_aan = get_metrics_table(metrics_config.get('aan_bal', []))
                df_zonder = get_metrics_table(metrics_config.get('zonder_bal', []))
                c1, c2 = st.columns(2)
                with c1: 
                    st.write("⚽ **Aan de Bal**")
                    if not df_aan.empty: st.dataframe(df_aan.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
                with c2: 
                    st.write("🛡️ **Zonder Bal**")
                    if not df_zonder.empty: st.dataframe(df_zonder.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
            else: st.info(f"Geen metrieken voor '{row['position']}'")

            # KPIs
            st.markdown("---"); st.subheader("📈 Impect Speler KPIs")
            kpis_config = get_config_for_position(row['position'], POSITION_KPIS)
            if kpis_config:
                def get_kpis_table(kpi_ids):
                    if not kpi_ids: return pd.DataFrame()
                    ids_tuple = tuple(str(x) for x in kpi_ids)
                    q = """SELECT d.name as "KPI", d.context as "Context", s.final_score_1_to_100 as "Score" FROM analysis.kpis_final_scores s JOIN analysis.kpi_definitions d ON CAST(s.metric_id AS TEXT) = d.id WHERE s."iterationId" = %s AND s."playerId" = %s AND s.metric_id IN %s ORDER BY s.final_score_1_to_100 DESC"""
                    return run_query(q, params=(selected_iteration_id, p_player_id, ids_tuple))
                df_k1 = get_kpis_table(kpis_config.get('aan_bal', []))
                df_k2 = get_kpis_table(kpis_config.get('zonder_bal', []))
                c1, c2 = st.columns(2)
                with c1: 
                    st.write("⚽ **Aan de Bal (KPIs)**")
                    if not df_k1.empty: st.dataframe(df_k1.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
                with c2: 
                    st.write("🛡️ **Zonder Bal (KPIs)**")
                    if not df_k2.empty: st.dataframe(df_k2.style.applymap(highlight_high_scores, subset=['Score']), use_container_width=True, hide_index=True)
            else: st.info("Geen KPIs gevonden.")

            # RAPPORTEN
            st.markdown("---"); st.subheader("📑 Data Scout Rapporten")
            reports_query = """
                SELECT m."scheduledDate" as "Datum", sq_h.name as "Thuisploeg", sq_a.name as "Uitploeg", r.position as "Positie", r.label as "Verdict"
                FROM analysis.scouting_reports r JOIN public.matches m ON r."matchId" = m.id LEFT JOIN public.squads sq_h ON m."homeSquadId" = sq_h.id LEFT JOIN public.squads sq_a ON m."awaySquadId" = sq_a.id
                WHERE r."iterationId" = %s AND r."playerId" = %s AND m.available = true ORDER BY m."scheduledDate" DESC
            """
            try:
                df_rep = run_query(reports_query, params=(selected_iteration_id, p_player_id))
                if not df_rep.empty:
                    c1, c2 = st.columns([2, 1])
                    with c1: st.dataframe(df_rep, use_container_width=True, hide_index=True)
                    with c2:
                        vc = df_rep['Verdict'].value_counts().reset_index(); vc.columns=['Verdict','Aantal']
                        fig = px.pie(vc, values='Aantal', names='Verdict', hole=0.4, color_discrete_sequence=['#d71920', '#bdc3c7', '#ecf0f1'])
                        st.plotly_chart(fig, use_container_width=True)
                else: st.info("Geen rapporten.")
            except: st.error("Fout bij laden rapporten.")

            # =========================================================
            # 7. VERGELIJKBARE SPELERS (GEOPTIMALISEERD & GEFILTERD)
            # =========================================================
            st.markdown("---")
            st.subheader("👯 Vergelijkbare Spelers (Op basis van Score & Stijl)")
            st.caption("Vergelijkt enkel met spelers uit seizoenen '25/26' en '2025' binnen het niveau (+/- 15 punten).")

            compare_columns = [col for col, score in profile_mapping.items() if score is not None and score > 0]
            reverse_mapping = {
                "KVK Centrale Verdediger": 'cb_kvk_score', "KVK Wingback": 'wb_kvk_score', "KVK Verdedigende Mid.": 'dm_kvk_score',
                "KVK Centrale Mid.": 'cm_kvk_score', "KVK Aanvallende Mid.": 'acm_kvk_score', "KVK Flank Aanvaller": 'fa_kvk_score',
                "KVK Spits": 'fw_kvk_score', "Voetballende CV": 'footballing_cb_kvk_score', "Controlerende CV": 'controlling_cb_kvk_score',
                "Verdedigende Back": 'defensive_wb_kvk_score', "Aanvallende Back": 'offensive_wingback_kvk_score', "Ballenafpakker (CVM)": 'ball_winning_dm_kvk_score',
                "Spelmaker (CVM)": 'playmaker_dm_kvk_score', "Box-to-Box (CM)": 'box_to_box_cm_kvk_score', "Diepgaande '10'": 'deep_running_acm_kvk_score',
                "Spelmakende '10'": 'playmaker_off_acm_kvk_score', "Buitenspeler (Binnendoor)": 'fa_inside_kvk_score', "Buitenspeler (Buitenom)": 'fa_wide_kvk_score',
                "Targetman": 'fw_target_kvk_score', "Lopende Spits": 'fw_running_kvk_score', "Afmaker": 'fw_finisher_kvk_score'
            }
            db_cols = [reverse_mapping[c] for c in compare_columns if c in reverse_mapping]

            if db_cols:
                with st.expander(f"Toon top 10 spelers die lijken op {selected_player_name}", expanded=False):
                    cols_str = ", ".join([f'a.{c}' for c in db_cols])
                    
                    # PERFORMANCE FILTER: AND i.season IN ('25/26', '2025') toegevoegd
                    sim_query = f"""
                        SELECT p.id as "playerId", p.commonname as "Naam", sq.name as "Team", i.season as "Seizoen", i."competitionName" as "Competitie", {cols_str}
                        FROM analysis.final_impect_scores a
                        JOIN public.players p ON CAST(a."playerId" AS TEXT) = CAST(p.id AS TEXT)
                        LEFT JOIN public.squads sq ON CAST(a."squadId" AS TEXT) = CAST(sq.id AS TEXT)
                        JOIN public.iterations i ON CAST(a."iterationId" AS TEXT) = CAST(i.id AS TEXT)
                        WHERE a.position = %s AND i.season IN ('25/26', '2025')
                    """
                    try:
                        df_all_p = run_query(sim_query, params=(row['position'],))
                        if not df_all_p.empty:
                            df_all_p['unique_id'] = df_all_p['playerId'].astype(str) + "_" + df_all_p['Seizoen']
                            df_all_p = df_all_p.drop_duplicates(subset=['unique_id']).set_index('unique_id')
                            
                            curr_uid = f"{p_player_id}_{selected_season}"
                            
                            if curr_uid in df_all_p.index:
                                target_vec = df_all_p.loc[curr_uid, db_cols]
                                target_avg = target_vec.mean()
                                others_avg = df_all_p[db_cols].mean(axis=1)
                                
                                # Niveau Filter
                                mask = (others_avg >= (target_avg - 15)) & (others_avg <= (target_avg + 15))
                                df_filtered = df_all_p[mask]
                                
                                if not df_filtered.empty:
                                    diff = (df_filtered[db_cols] - target_vec).abs().mean(axis=1)
                                    sim = (100 - diff).sort_values(ascending=False)
                                    if curr_uid in sim.index: sim = sim.drop(curr_uid)
                                    
                                    top_10 = sim.head(10).index
                                    results = df_filtered.loc[top_10].copy()
                                    results['Gelijkenis %'] = sim.loc[top_10]
                                    results['Avg Score'] = others_avg.loc[top_10]
                                    
                                    def color_sim(val):
                                        c = '#2ecc71' if val > 90 else '#27ae60' if val > 80 else 'black'
                                        w = 'bold' if val > 80 else 'normal'
                                        return f'color: {c}; font-weight: {w}'

                                    disp_df = results[['Naam', 'Team', 'Seizoen', 'Competitie', 'Avg Score', 'Gelijkenis %']].reset_index(drop=True)
                                    
                                    event = st.dataframe(
                                        disp_df.style.applymap(color_sim, subset=['Gelijkenis %']).format({'Gelijkenis %': '{:.1f}%', 'Avg Score': '{:.1f}'}),
                                        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
                                    )
                                    
                                    if len(event.selection.rows) > 0:
                                        idx = event.selection.rows[0]
                                        cr = disp_df.iloc[idx]
                                        st.session_state.pending_nav = {"season": cr['Seizoen'], "competition": cr['Competitie'], "target_name": cr['Naam'], "mode": "Spelers"}
                                        st.rerun()
                                else: st.warning("Geen spelers van dit niveau gevonden in 25/26 of 2025.")
                            else: st.warning("Huidige speler niet gevonden in recente seizoenen.")
                        else: st.info("Geen vergelijkbare spelers in 25/26 of 2025.")
                    except Exception as e: st.error("Fout bij berekenen."); st.code(e)
            else: st.info("Geen profielscores.")
        else: st.error("Geen data.")
    except Exception as e: st.error("Fout bij ophalen speler details."); st.code(e)

# =============================================================================
# B. TEAMS MODUS
# =============================================================================
elif analysis_mode == "Teams":
    st.header("🛡️ Team Analyse")
    st.sidebar.header("3. Team Selectie")
    teams_query = """SELECT DISTINCT sq.name, sq.id as "squadId" FROM public.squads sq JOIN analysis.squad_final_scores s ON sq.id = s."squadId" WHERE s."iterationId" = %s ORDER BY sq.name;"""
    try:
        df_teams = run_query(teams_query, params=(selected_iteration_id,))
        team_names = df_teams['name'].tolist()
        selected_team_name = st.sidebar.selectbox("Kies een team:", team_names, key="sb_team")
        candidate = df_teams[df_teams['name'] == selected_team_name]
        
        final_squad_id = None
        if len(candidate) > 1:
            st.sidebar.warning("Meerdere teams gevonden.")
            opts = candidate.apply(lambda x: f"{x['name']} (ID: {x['squadId']})", axis=1).tolist()
            sel = st.sidebar.selectbox("Specifieer:", opts)
            final_squad_id = sel.split("ID: ")[1].replace(")", "")
        elif len(candidate) == 1: final_squad_id = candidate.iloc[0]['squadId']
        else: st.error("Geen team gevonden."); st.stop()
        
        if final_squad_id:
            st.divider()
            t_dets = run_query('SELECT name, "imageUrl" FROM public.squads WHERE id = %s', params=(final_squad_id,))
            if not t_dets.empty:
                t_row = t_dets.iloc[0]
                c1, c2 = st.columns([1, 5])
                with c1: 
                    if t_row['imageUrl']: st.image(t_row['imageUrl'], width=100)
                with c2: st.header(f"🛡️ {t_row['name']}")
                
                # Profielen
                st.divider(); st.subheader("📊 Team Profiel Scores")
                prof_q = 'SELECT profile_name as "Profiel", score as "Score" FROM analysis.squad_profile_scores WHERE "squadId" = %s AND "iterationId" = %s ORDER BY score DESC'
                try:
                    df_p = run_query(prof_q, params=(final_squad_id, selected_iteration_id))
                    if not df_p.empty:
                        c1, c2 = st.columns([1, 2])
                        def hl(v): return 'color: #2ecc71; font-weight: bold' if isinstance(v, (int,float)) and v > 66 else ''
                        with c1: st.dataframe(df_p.style.applymap(hl, subset=['Score']).format({'Score': '{:.1f}'}), use_container_width=True, hide_index=True)
                        with c2: 
                            fig = px.bar(df_p, x='Profiel', y='Score', color_discrete_sequence=['#d71920'])
                            st.plotly_chart(fig, use_container_width=True)
                    else: st.info("Geen profielen.")
                except: st.error("Fout profielen.")

                # Inverted highlight
                def hl_inv(v): return 'background-color: #e74c3c; color: white; font-weight: bold' if str(v).lower().strip() == 'true' else ''

                # Metrieken
                with st.expander("📊 Team Impect Scores (Metrieken)", expanded=False):
                    q = 'SELECT d.name as "Metriek", d.details_label as "Detail", d.inverted as "Inverted", s.final_score_1_to_100 as "Score" FROM analysis.squad_final_scores s JOIN public.squad_score_definitions d ON d.id = REPLACE(s.metric_id, \'s\', \'\') WHERE s."squadId" = %s AND s."iterationId" = %s ORDER BY s.final_score_1_to_100 DESC'
                    try:
                        df = run_query(q, params=(final_squad_id, selected_iteration_id))
                        if not df.empty: st.dataframe(df.style.applymap(hl, subset=['Score']).applymap(hl_inv, subset=['Inverted']).format({'Score': '{:.1f}'}), use_container_width=True, hide_index=True)
                        else: st.info("Geen data.")
                    except: st.error("Fout metrieken.")

                # KPIs
                with st.expander("📉 Team Impect KPIs (Details)", expanded=False):
                    q = 'SELECT d.name as "KPI", s.final_score_1_to_100 as "Score" FROM analysis.squadkpi_final_scores s JOIN analysis.kpi_definitions d ON d.id = REPLACE(s.metric_id, \'k\', \'\') WHERE s."squadId" = %s AND s."iterationId" = %s ORDER BY s.final_score_1_to_100 DESC'
                    try:
                        df = run_query(q, params=(final_squad_id, selected_iteration_id))
                        if not df.empty: st.dataframe(df.style.applymap(hl, subset=['Score']).format({'Score': '{:.1f}'}), use_container_width=True, hide_index=True)
                        else: st.info("Geen data.")
                    except: st.error("Fout KPIs.")

                # SIMILARITY (PERFORMANCE FILTER: 25/26 & 2025)
                st.markdown("---"); st.subheader("🤝 Vergelijkbare Teams")
                st.caption("Vergelijkt enkel met teams uit seizoenen '25/26' en '2025'.")
                
                # PERFORMANCE FILTER TOEGEVOEGD
                all_prof_q = """
                    SELECT s."squadId", sq.name as "Team", i.season as "Seizoen", i."competitionName" as "Competitie", s.profile_name, s.score 
                    FROM analysis.squad_profile_scores s 
                    JOIN public.squads sq ON s."squadId" = sq.id 
                    JOIN public.iterations i ON s."iterationId" = i.id
                    WHERE i.season IN ('25/26', '2025')
                """
                try:
                    df_all = run_query(all_prof_q)
                    if not df_all.empty:
                        df_piv = df_all.pivot_table(index=['squadId', 'Team', 'Seizoen', 'Competitie'], columns='profile_name', values='score').fillna(0)
                        curr_seas = selected_season
                        
                        if (final_squad_id, t_row['name'], curr_seas, selected_competition) in df_piv.index:
                            target = df_piv.loc[(final_squad_id, t_row['name'], curr_seas, selected_competition)]
                            diff = (df_piv - target).abs().mean(axis=1)
                            sim = (100 - diff).sort_values(ascending=False)
                            sim = sim[sim.index != (final_squad_id, t_row['name'], curr_seas, selected_competition)]
                            
                            top5 = sim.head(5).reset_index(); top5.columns = ['ID', 'Team', 'Seizoen', 'Competitie', 'Gelijkenis %']
                            def c_sim(v): 
                                c = '#2ecc71' if v > 90 else '#27ae60' if v > 80 else 'black'
                                w = 'bold' if v > 80 else 'normal'
                                return f'color: {c}; font-weight: {w}'
                            
                            disp = top5[['Team', 'Seizoen', 'Competitie', 'Gelijkenis %']]
                            ev = st.dataframe(disp.style.applymap(c_sim, subset=['Gelijkenis %']).format({'Gelijkenis %': '{:.1f}%'}), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
                            
                            if len(ev.selection.rows) > 0:
                                idx = ev.selection.rows[0]; cr = disp.iloc[idx]
                                st.session_state.pending_nav = {"season": cr['Seizoen'], "competition": cr['Competitie'], "target_name": cr['Team'], "mode": "Teams"}
                                st.rerun()
                        else: st.warning("Team niet gevonden in recente data.")
                    else: st.info("Geen teams gevonden in 25/26 of 2025.")
                except Exception as e: st.error("Fout similarity."); st.code(e)
            else: st.error("Team details fout.")
    except Exception as e: st.error("Teamlijst fout."); st.code(e)

elif analysis_mode == "Coaches":
    st.header("👔 Coach Analyse")
    st.warning("🚧 Work in Progress")
