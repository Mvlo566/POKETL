import os
import psycopg2
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv(".env")

# Fonction de connexion PostgreSQL
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

# Fonction pour afficher le nombre de deck_id et deck_instance_id distincts
def count_deck_ids():
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT deck_id) FROM public.wrk_decklists")
            total_deck_id = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT deck_instance_id) FROM public.wrk_decklists")
            total_instance_id = cur.fetchone()[0]

            print(f"[📦] deck_id uniques         : {total_deck_id}")
            print(f"[🧬] deck_instance_id uniques : {total_instance_id}")
    except Exception as e:
        print(f"[❌] Erreur : {e}")

# Exécution principale
if __name__ == "__main__":
    count_deck_ids()
