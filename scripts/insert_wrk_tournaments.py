from dotenv import load_dotenv
import os
import psycopg2
from collections import defaultdict
from psycopg2.extras import execute_values
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Chargement des variables d'environnement
load_dotenv(dotenv_path=".env")

postgres_db = os.getenv('POSTGRES_DB')
postgres_user = os.getenv('POSTGRES_USER')
postgres_password = os.getenv('POSTGRES_PASSWORD')
postgres_host = os.getenv('POSTGRES_HOST')
postgres_port = os.getenv('POSTGRES_PORT')

def get_connection_string():
    return f"host={postgres_host} port={postgres_port} dbname={postgres_db} user={postgres_user} password={postgres_password}"

def log(msg):
    print(f"[LOG] {msg}")

def add_newest_set_column():
    try:
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    ALTER TABLE public.wrk_tournaments
                    ADD COLUMN IF NOT EXISTS newest_set varchar;
                """)
            conn.commit()
        log("✅ Colonne newest_set ajoutée à wrk_tournaments.")
    except Exception as e:
        log(f"❌ Erreur ajout colonne newest_set : {e}")
        exit(1)

def update_newest_set_by_tournament():
    try:
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tournament_id, newest_set
                    FROM public.wrk_decklists
                    WHERE newest_set IS NOT NULL;
                """)
                rows = cur.fetchall()

        # Priorité des sets
        set_priority = {
            "A1": 1,
            "A1a": 2,
            "A2": 3,
            "A2a": 4,
            "A2b": 5,
            "A3": 6,
            "A3a": 7
        }

        tournament_sets = defaultdict(set)

        for tournament_id, newest_set in rows:
            ns = (newest_set or "").strip()
            if ns in set_priority:
                tournament_sets[tournament_id].add(ns)

        updates = []
        for tid, sets in tournament_sets.items():
            most_recent = max(sets, key=lambda s: set_priority[s])
            updates.append((most_recent, tid))

        log(f"📊 Mise à jour de {len(updates)} tournois avec leur newest_set...")

        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                execute_values(cur, """
                    UPDATE public.wrk_tournaments AS t
                    SET newest_set = v.newest_set
                    FROM (VALUES %s) AS v(newest_set, tournament_id)
                    WHERE t.tournament_id = v.tournament_id
                """, updates)
            conn.commit()

        log("✅ Mise à jour des newest_set terminée.")

        # Patch des tournois sans aucun deck
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE public.wrk_tournaments
                    SET newest_set = 'Unknown'
                    WHERE tournament_id NOT IN (
                        SELECT DISTINCT tournament_id FROM public.wrk_decklists
                    );
                """)
            conn.commit()
        log("🩹 Patch : 'Unknown' appliqué aux tournois sans deck.")
    except Exception as e:
        log(f"❌ Erreur update newest_set : {e}")
        exit(1)

if __name__ == "__main__":
    log("🚀 Script de mise à jour newest_set par tournoi lancé")
    add_newest_set_column()
    update_newest_set_by_tournament()
    log("✅ Script terminé.")
