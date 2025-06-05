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

def create_wrk_players_table():
    ddl = """
    DROP TABLE IF EXISTS public.wrk_players;
    CREATE TABLE public.wrk_players (
      player_id varchar PRIMARY KEY,
      player_name varchar,
      player_country varchar
    );
    """
    with psycopg2.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    log("✅ Table 'wrk_players' créée ou recréée")

def insert_wrk_players():
    player_dict = {}

    for file in os.listdir(output_directory):
        path = os.path.join(output_directory, file)
        with open(path, encoding="utf-8") as f:
            tournament = json.load(f)
            for player in tournament.get("players", []):
                pid = player["id"]
                if pid not in player_dict:
                    player_dict[pid] = (
                        pid,
                        player.get("name", None),
                        player.get("country", None)
                    )

    player_data = list(player_dict.values())

    with psycopg2.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO public.wrk_players 
                (player_id, player_name, player_country)
                VALUES %s
                ON CONFLICT (player_id) DO NOTHING;
            """, player_data)
        conn.commit()
        log(f"✅ {len(player_data)} joueurs insérés")

if __name__ == "__main__":
    log("🧠 Initialisation insert_wrk_players")
    create_wrk_players_table()
    insert_wrk_players()
    log("🏁 Import des joueurs terminé")
