from dotenv import load_dotenv
import os
import psycopg2
import json
from psycopg2.extras import execute_values
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Load .env
load_dotenv(dotenv_path=".env")

# Env vars
postgres_db = os.getenv('POSTGRES_DB')
postgres_user = os.getenv('POSTGRES_USER')
postgres_password = os.getenv('POSTGRES_PASSWORD')
postgres_host = os.getenv('POSTGRES_HOST')
postgres_port = os.getenv('POSTGRES_PORT')

output_directory = "./sample_output"

def get_connection_string():
    return f"host={postgres_host} port={postgres_port} dbname={postgres_db} user={postgres_user} password={postgres_password}"

def log(msg):
    print(f"[LOG] {msg}")

def create_wrk_matches_table():
    sql = """
    DROP TABLE IF EXISTS public.wrk_matches;

    CREATE TABLE public.wrk_matches (
        match_id varchar PRIMARY KEY,
        tournament_id varchar,
        player1_id varchar,
        player2_id varchar,
        player1_score int,
        player2_score int,
        player1_deck_id varchar,
        player2_deck_id varchar
    );
    """
    try:
        log("📜 Création de la table wrk_matches...")
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        log("✅ Table wrk_matches recréée avec colonnes deck_id.")
    except Exception as e:
        log(f"❌ Erreur création table wrk_matches : {e}")
        exit(1)

def load_deck_ids():
    query = """
        SELECT DISTINCT tournament_id, player_id, deck_id
        FROM public.wrk_decklists
    """
    try:
        log("🔄 Chargement des deck_id depuis wrk_decklists...")
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                result = {(row[0], row[1].strip().lower()): row[2] for row in cur.fetchall()}
        log(f"✅ {len(result)} deck_id chargés en mémoire")
        return result
    except Exception as e:
        log(f"❌ Erreur lors du chargement des deck_id : {e}")
        exit(1)

def insert_wrk_matches(batch_size=100000):
    match_data = []
    match_id_counter = 1
    deck_lookup = load_deck_ids()

    log("📁 Parcours des fichiers JSON...")
    for file in os.listdir(output_directory):
        path = os.path.join(output_directory, file)
        log(f"📄 Lecture : {file}")
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                tournament = json.load(f)
                tournament_id = tournament.get("id")

                matches = tournament.get("match_results") or tournament.get("matches")
                if not matches:
                    log(f"⚠️ Aucun match trouvé dans {file}")
                    continue

                for match in matches:
                    m = match.get("match_results")
                    if not m or len(m) != 2:
                        log(f"❌ Format match invalide dans {file}")
                        continue

                    p1_id = m[0]["player_id"].strip().lower()
                    p1_score = m[0]["score"]
                    p2_id = m[1]["player_id"].strip().lower()
                    p2_score = m[1]["score"]

                    # Skip match if both scores are 0
                    if p1_score == 0 and p2_score == 0:
                        continue

                    p1_deck = deck_lookup.get((tournament_id, p1_id))
                    p2_deck = deck_lookup.get((tournament_id, p2_id))

                    # Skip match if one of the decks is missing
                    if not p1_deck or not p2_deck:
                        continue

                    match_id = str(match_id_counter).zfill(10)
                    match_data.append((
                        match_id,
                        tournament_id,
                        p1_id,
                        p2_id,
                        p1_score,
                        p2_score,
                        p1_deck,
                        p2_deck
                    ))
                    match_id_counter += 1
            log(f"✅ {match_id_counter - 1} matchs extraits jusqu'ici")
        except Exception as e:
            log(f"❌ Erreur lecture {file} : {e}")

    try:
        with psycopg2.connect(get_connection_string()) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                log(f"🚀 Insertion en base en batchs de {batch_size}...")
                for i in range(0, len(match_data), batch_size):
                    chunk = match_data[i:i + batch_size]
                    log(f"📤 Insertion batch {i} → {i + len(chunk)}")
                    execute_values(cur, """
                        INSERT INTO public.wrk_matches 
                        (match_id, tournament_id, player1_id, player2_id, player1_score, player2_score, player1_deck_id, player2_deck_id)
                        VALUES %s
                        ON CONFLICT DO NOTHING;
                    """, chunk)
                    log(f"✅ Batch {i} → {i + len(chunk)} inséré")
        log(f"✅ Total : {len(match_data)} matchs insérés avec deck_id")
    except Exception as e:
        log(f"❌ Erreur insertion finale : {e}")
        exit(1)

if __name__ == "__main__":
    log("🧠 Initialisation insert_wrk_matches")
    create_wrk_matches_table()
    insert_wrk_matches()
    log("🏁 Import des matchs terminé")
