import streamlit as st
import pandas as pd
import psycopg2

st.set_page_config(page_title="Scouting App", page_icon="⚽", layout="wide")

# Titel
st.title("⚽ Voetbal Data Analyse - Hoofdoverzicht")

# Database connectie functie
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["dbname"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"]
    )

# Data ophalen functie
@st.cache_data(ttl=600) # ttl=600 betekent: onthoud deze data 10 minuten, scheelt laadtijd
def run_query(query):
    conn = init_connection()
    return pd.read_sql(query, conn)

# De Query: We pakken de top 50 spelers uit de analysis tabel
# En we 'joinen' (koppelen) de namen tabel erbij
sql_query = """
    SELECT 
        t.Spelersnaam,
        t.Leeftijd,  -- Als deze kolom bestaat in players_squads_info
        t.Positie,   -- Even gokken dat deze kolom zo heet, pas aan indien nodig!
        a.cb_kvk_score as "Score CV",
        a.playmaker_dm_kvk_score as "Score CVM"
    FROM analysis.final_impect_scores a
    JOIN tabellen.players_squads_info t ON a.playerId = t.Speler_ID
    LIMIT 50;
"""

try:
    # Voer de query uit
    df = run_query(sql_query)
    
    # Toon de data
    st.subheader("Top Spelers (Ruwe Data)")
    st.dataframe(df)

except Exception as e:
    st.error("❌ Er ging iets mis met de query.")
    st.warning("Waarschijnlijk kloppen de kolomnamen niet helemaal. Check de error hieronder:")
    st.code(e)
