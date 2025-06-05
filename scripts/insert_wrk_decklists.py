from dotenv import load_dotenv
import os
import psycopg2
import json
import re
from multiprocessing import Pool, cpu_count
from psycopg2.extras import execute_values
from collections import Counter, defaultdict
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

def extract_card_id(card_url):
    if not card_url:
        return None
    match = re.search(r"cards/([^/]+)/(\d+)", card_url)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    return None

def create_table():
    log("💣 Suppression de la table wrk_decklists si existante (reset complet)")
    sql = """
    DROP TABLE IF EXISTS public.wrk_decklists;

    CREATE TABLE public.wrk_decklists (
        deck_id varchar,
        deck_instance_id varchar,
        tournament_id varchar,
        player_id varchar,
        card_id varchar,
        card_count int,
        family_deck TEXT,
        main_set TEXT,
        newest_set TEXT,
        PRIMARY KEY (deck_id, tournament_id, player_id, card_id)
    );
    """
    try:
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        log("✅ Table wrk_decklists recréée avec deck_id.")
    except Exception as e:
        log(f"❌ Erreur création table : {e}")
        exit(1)

def process_file(file):
    path = f"{output_directory}/{file}"
    log(f"🔍 Traitement : {file}")

    if os.path.getsize(path) < 1000:
        log(f"⚠️ Fichier ignoré (trop petit) : {file}")
        return []

    batch = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
            tournament_id = data['id'].strip().lower()
            for player in data['players']:
                player_id = player['id'].strip().lower()
                cards = []
                for card in player['decklist']:
                    card_id = extract_card_id(card.get('url'))
                    if card_id:
                        cards.append((card_id, int(card['count'])))
                if cards:
                    batch.append((tournament_id, player_id, cards))
        log(f"✅ {len(batch)} decks trouvés dans {file}")
    except Exception as e:
        log(f"❌ Erreur fichier {file} : {e}")
    return batch

def generate_deck_ids(deck_data):
    deck_map = {}
    deck_instance_map = {}
    id_counter = 1
    instance_counter = 1
    all_rows = []
    deck_usage = Counter()

    for tournament_id, player_id, cards in deck_data:
        sorted_cards = tuple(sorted(cards))  # Pour deck_instance_id
        key_instance = (tournament_id, sorted_cards)
        if key_instance not in deck_instance_map:
            deck_instance_map[key_instance] = f"{instance_counter:06}"
            instance_counter += 1
        deck_instance_id = deck_instance_map[key_instance]

        key = (tournament_id, player_id)  # Pour deck_id
        if key not in deck_map:
            deck_map[key] = f"{id_counter:06}"
            id_counter += 1
        deck_id = deck_map[key]
        deck_usage[deck_id] += 1

        for card_id, count in cards:
            all_rows.append((deck_id, deck_instance_id, tournament_id, player_id, card_id, count))

    return all_rows, len(deck_map), deck_usage.most_common(10)


def insert_decklists(batch_size=100000):
    log(f"📁 Lecture du dossier : {output_directory}")
    files = [f for f in os.listdir(output_directory) if f.endswith(".json")]
    log(f"📂 {len(files)} fichiers JSON détectés.")

    try:
        log(f"🧠 Lancement du multiprocessing ({cpu_count()} cœurs CPU)...")
        with Pool(cpu_count()) as pool:
            results = pool.map(process_file, files)
        log("✅ Multiprocessing terminé.")
    except Exception as e:
        log(f"❌ Erreur multiprocessing : {e}")
        exit(1)

    flat_deck_data = [deck for sublist in results for deck in sublist]
    all_rows, deck_count, top_10 = generate_deck_ids(flat_deck_data)

    log(f"📊 {len(all_rows)} lignes générées.")

    inserted = 0
    try:
        with psycopg2.connect(get_connection_string()) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                log("🚀 Insertion en base...")
                for i in range(0, len(all_rows), batch_size):
                    chunk = all_rows[i:i + batch_size]
                    log(f"📤 Batch {i} → {i + len(chunk)}")
                    execute_values(cur, """
                        INSERT INTO public.wrk_decklists 
                        (deck_id, deck_instance_id, tournament_id, player_id, card_id, card_count)
                        VALUES %s
                    """, chunk, page_size=batch_size)

                    inserted += len(chunk)
                    log(f"✅ {inserted}/{len(all_rows)} lignes insérées")
    except Exception as e:
        log(f"❌ Erreur insertion : {e}")
        exit(1)

    log(f"🌾 Insertion terminée.")
    log(f"📦 {deck_count} decks uniques détectés.")
    log("🏆 Top 10 des deck_id les plus utilisés :")
    for deck_instance_id, count in top_10:
        log(f"   → {deck_instance_id} : {count} joueurs")

def update_family_decks_and_main_set():
    log("🦠 Génération des family_deck, main_set et newest_set (par deck_id)...")
    try:
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                # Toutes les cartes (pour main_set et newest_set)
                log("📦 Récupération de toutes les cartes...")
                cur.execute("""
                    SELECT deck_id, card_id, card_count
                    FROM public.wrk_decklists
                """)
                all_rows = cur.fetchall()

                # Cartes Pokémon uniquement (pour family_deck)
                log("🧬 Récupération des cartes Pokémon...")
                cur.execute("""
                    SELECT d.deck_id, d.card_id, d.card_count, c.card_name, c.evolution_n1, c.stage_evo
                    FROM public.wrk_decklists d
                    JOIN public.dwh_cards c ON d.card_id = c.card_id
                    WHERE c.card_type = 'Pokémon' AND c.card_name IS NOT NULL
                """)
                poke_rows = cur.fetchall()

        decks_sets = defaultdict(lambda: Counter())
        decks_cards = defaultdict(list)

        for deck_id, card_id, count in all_rows:
            set_prefix = card_id.split('_')[0]
            decks_sets[deck_id][set_prefix] += count

        for deck_id, card_id, count, name, evo_from, stage in poke_rows:
            try:
                stage_int = int(stage) if stage and stage.isdigit() else -1
            except:
                stage_int = -1
            decks_cards[deck_id].append({
                "name": name.strip(),
                "evolution_n1": evo_from.strip() if evo_from else None,
                "stage": stage_int
            })

        set_priority = {"A1": 1, "A1a": 2, "A2": 3, "A2a": 4, "A2b": 5, "A3": 6}
        updates = []

        for deck_id in decks_sets.keys():
            cards = decks_cards[deck_id]
            set_counter = decks_sets[deck_id]

            # MAIN SET (exclut P-A)
            most_common_sets = [s for s in set_counter.most_common() if s[0] != "P-A"]
            main_set = most_common_sets[0][0] if most_common_sets else None

            # NEWEST SET (prend la plus haute priorité ou fallback main_set)
            known_sets = [s for s in set_counter if s in set_priority]
            newest_set = max(known_sets, key=lambda x: set_priority[x]) if known_sets else main_set

            # FAMILY DECK uniquement avec Pokémon
            all_names = set(card["name"] for card in cards)
            evo_sources = set(card["evolution_n1"] for card in cards if card["evolution_n1"])
            final_cards = [(card["name"], card["stage"]) for card in cards if card["name"] not in evo_sources]
            final_cards = sorted(final_cards, key=lambda x: (-x[1], x[0]))
            top_names = [name for name, _ in final_cards[:5]]

            name_clean = lambda n: re.sub(r"\s+ex$", "", n.strip(), flags=re.IGNORECASE)
            dedup = {}
            for n in top_names:
                base = name_clean(n)
                if base not in dedup or "ex" in n.lower():
                    dedup[base] = n
            final = sorted(set(dedup.values()))
            if len(final) > 10:
                final = final[:10]
            family_name = " + ".join(final)

            updates.append((family_name, main_set, newest_set, deck_id))

        log(f"✏️ Mise à jour en base de {len(updates)} family_deck + main_set + newest_set...")

        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                execute_values(cur, """
                    UPDATE public.wrk_decklists AS d SET 
                        family_deck = v.family_deck,
                        main_set = v.main_set,
                        newest_set = v.newest_set
                    FROM (VALUES %s) AS v(family_deck, main_set, newest_set, deck_id)
                    WHERE d.deck_id = v.deck_id
                """, updates, page_size=10000)
            conn.commit()
        log("✅ Mise à jour massive terminée.")
    except Exception as e:
        log(f"❌ Erreur enrichissement family_deck + main_set + newest_set : {e}")
        exit(1)


if __name__ == "__main__":
    log("🚀 Script decklists lancé.")
    create_table()
    insert_decklists()
    update_family_decks_and_main_set()
    log("✅ Script terminé.")
