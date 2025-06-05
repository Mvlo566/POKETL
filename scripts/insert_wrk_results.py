from dotenv import load_dotenv
import os
import psycopg2
import json
import time
from psycopg2.extras import execute_values
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Load .env
load_dotenv(dotenv_path=".env")

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

def create_wrk_results_table():
    ddl = """
    DROP TABLE IF EXISTS public.wrk_results;
    CREATE TABLE public.wrk_results (
      tournament_id varchar,
      player_id varchar,
      "placing" int,
      PRIMARY KEY (tournament_id, player_id)
    );
    """
    with psycopg2.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    log("✅ Table 'wrk_results' créée ou recréée")

def insert_wrk_results():
    log("📁 Chargement des fichiers JSON...")
    files = os.listdir(output_directory)
    total_files = len(files)
    log(f"📊 {total_files} fichiers trouvés")

    results = []
    start = time.time()

    for idx, file in enumerate(files, 1):
        path = os.path.join(output_directory, file)
        try:
            with open(path, encoding="utf-8") as f:
                tournament = json.load(f)
                tournament_id = tournament["id"]
                for player in tournament.get("players", []):
                    player_id = player["id"]
                    placing = int(player.get("placing", -1))
                    results.append((tournament_id, player_id, placing))
        except Exception as e:
            log(f"❌ Erreur fichier {file} : {e}")

        if idx % 50 == 0 or idx == total_files:
            elapsed = time.time() - start
            avg_time = elapsed / idx
            est_total = avg_time * total_files
            eta = est_total - elapsed
            log(f"🕒 Fichiers traités : {idx}/{total_files} ({(idx/total_files)*100:.1f}%) - ETA : {eta:.1f}s")

    log(f"📥 Insertion de {len(results)} lignes dans wrk_results...")

    if results[:3]:
        log(f"🔎 Exemple : {results[:3]}")

    with psycopg2.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO public.wrk_results 
                (tournament_id, player_id, "placing")
                VALUES %s
                ON CONFLICT (tournament_id, player_id) DO NOTHING;
            """, results)
        conn.commit()

    duration = time.time() - start
    log(f"✅ {len(results)} résultats insérés en {duration:.2f} secondes.")

if __name__ == "__main__":
    log("🧠 Initialisation insert_wrk_results")
    create_wrk_results_table()
    insert_wrk_results()
    log("🏁 Script terminé")
