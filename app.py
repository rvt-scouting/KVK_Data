import streamlit as st
import pandas as pd
import psycopg2

# 1. Paginaconfiguratie (Tabblad naam en icon)
st.set_page_config(page_title="Scouting App", page_icon="⚽")

# 2. Titel op het scherm
st.title("⚽ Voetbal Data Analyse")
st.write("Welkom! We testen nu de verbinding met de database...")

# 3. De functie om verbinding te maken
# We gebruiken st.cache_resource zodat hij niet bij elke klik opnieuw inlogt (dat is traag)
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["dbname"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"]
    )

# 4. Probeer data op te halen
try:
    conn = init_connection()
    # We halen even simpelweg de versie op om te testen of het werkt
    query = "SELECT version();"
    
    # We gebruiken Pandas om de SQL uit te voeren en er een nette tabel van te maken
    df = pd.read_sql(query, conn)
    
    st.success("✅ Verbinding geslaagd!")
    st.write("Database versie:")
    st.dataframe(df)
    
except Exception as e:
    st.error("❌ Er ging iets mis met de verbinding.")
    st.error(e)
