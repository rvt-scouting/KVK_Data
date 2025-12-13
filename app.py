import os
import sys
import psycopg2
from dotenv import load_dotenv

# --- CONFIGURATIE -----------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_PARAMS = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASS"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT", "5432")
}

# --- DE SPEELSTIJLEN DEFINITIES ---
SQUAD_STYLES = {
    "KVK STYLE OF PLAY":      [1282, 1611, 1007, 412, 162, 161, 87, 40],
    "Heavy Metal":            [24, 162, 1279, 412, 1610, 464],
    "Counter Attacking":      [162, 266, 265, 899, 40],
    "Underdog Pressure":      [901, 900, 162, 1161],
    "Direct and Aerial":      [1610, 464, 113, 96, 165, 24, 16],
    "Possession and Control": [19, 161, 106, 413, 1278, 39, 21],
    "Safety First":           [694, 1463, 108]
}

SOURCE_TABLE = "analysis.squadKPI_final_scores"
TARGET_TABLE = "analysis.squad_profile_scores"

# --- FUNCTIES ---------------------------------------------------------

def setup_database(conn):
    """Maakt de doeltabel aan."""
    print("🛠️  Tabel structuur aanmaken...")
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS analysis;")
        cur.execute(f"""
            DROP TABLE IF EXISTS {TARGET_TABLE};
            
            CREATE TABLE {TARGET_TABLE} (
                "squadId" TEXT,
                "iterationId" TEXT,
                "profile_name" TEXT,
                "score" INT, -- Genormaliseerde score (fair)
                "raw_avg" NUMERIC(10,2), -- Het originele gemiddelde (voor debug)
                PRIMARY KEY ("squadId", "iterationId", "profile_name")
            );
        """)
        conn.commit()

def calculate_profiles(conn):
    """Berekent het gemiddelde per stijl en normaliseert dit vervolgens."""
    print("📊 Berekenen van Squad Speelstijlen (Fair Method)...")
    
    with conn.cursor() as cur:
        for style_name, kpi_ids in SQUAD_STYLES.items():
            formatted_ids = [f"'k{x}'" for x in kpi_ids]
            id_string = ", ".join(formatted_ids)
            
            # DE MAGISCHE QUERY
            # Stap 1: Bereken het ruwe gemiddelde (RawStats)
            # Stap 2: Bereken stats over die ruwe gemiddeldes (LeagueStats)
            # Stap 3: Normaliseer naar 1-100 (Final)
            query = f"""
                WITH RawStats AS (
                    SELECT 
                        "squadId",
                        "iterationId",
                        AVG(final_score_1_to_100) as raw_score
                    FROM 
                        {SOURCE_TABLE}
                    WHERE 
                        metric_id IN ({id_string})
                    GROUP BY 
                        "squadId", "iterationId"
                ),
                LeagueStats AS (
                    SELECT
                        "iterationId",
                        AVG(raw_score) as league_mean,
                        STDDEV(raw_score) as league_std
                    FROM RawStats
                    GROUP BY "iterationId"
                )
                INSERT INTO {TARGET_TABLE} ("squadId", "iterationId", "profile_name", "score", "raw_avg")
                SELECT 
                    r."squadId",
                    r."iterationId",
                    '{style_name}' as profile_name,
                    -- De Z-Score Transformatie op het PROFIEL zelf
                    ROUND(
                        LEAST(100.0, GREATEST(1.0, 
                            50.0 + (
                                CASE 
                                    WHEN l.league_std = 0 THEN 0
                                    ELSE (r.raw_score - l.league_mean) / l.league_std 
                                END
                            ) * 16.0
                        ))
                    )::INT as score,
                    r.raw_score
                FROM 
                    RawStats r
                JOIN 
                    LeagueStats l ON r."iterationId" = l."iterationId";
            """
            
            cur.execute(query)
            print(f"   👉 '{style_name}': {cur.rowcount} teams berekend.")
            
        conn.commit()

def run():
    print(f"\n🚀 C22 - Squad Profiles Calculation (Fair Logic) gestart")
    
    if not all(DB_PARAMS.values()):
        print("❌ Database credentials ontbreken.")
        sys.exit(1)

    conn = psycopg2.connect(**DB_PARAMS)
    try:
        setup_database(conn)
        calculate_profiles(conn)
        print(f"✅ Klaar! Resultaten staan in {TARGET_TABLE}.")
    except Exception as e:
        print(f"❌ Fout: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run()
