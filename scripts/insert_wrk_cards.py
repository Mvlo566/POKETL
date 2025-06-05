from dotenv import load_dotenv
import os
import psycopg2
import requests
from lxml import html
import re
import json
from pathlib import Path
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
json_folder = "./sample_output"

def get_connection_string():
    return f"host={postgres_host} port={postgres_port} dbname={postgres_db} user={postgres_user} password={postgres_password}"

def log(msg):
    print(f"[LOG] {msg}")

def extract_card_data_from_json(json_folder):
    records = set()
    for file in Path(json_folder).rglob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for player in data.get("players", []):
                    for card in player.get("decklist", []):
                        url = card.get("url")
                        card_type = card.get("type")
                        card_name_raw = card.get("name", "")
                        match = re.search(r"cards/([^/]+)/(\d+)", url or "")
                        if match:
                            card_set = match.group(1)
                            card_number = match.group(2)
                            card_id = f"{card_set}_{card_number}"
                            card_name = re.sub(r"\s+\([A-Z0-9a-z\-]+\)$", "", card_name_raw)
                            records.add((card_id, card_set, card_number, card_type, card_name, url))
        except Exception as e:
            log(f"⚠️ Erreur JSON {file}: {e}")
    return list(records)

def get_card_details(card_set, card_number):
    try:
        url = f"https://pocket.limitlesstcg.com/cards/{card_set}/{card_number}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=5, headers=headers)
        tree = html.fromstring(response.content)

        subtype, hp, illustrator, evo_n1, stage_evo = None, None, None, None, None

        # Subtype + HP
        text_list = tree.xpath('//p[@class="card-text-title"]/text()[normalize-space()]')
        if text_list:
            raw = text_list[0].strip()
            match = re.search(r"-\s*(.*?)\s*-\s*(\d+)\s*HP", raw)
            if match:
                subtype = match.group(1)
                hp = int(match.group(2))

        # Illustrator
        illustrator_list = tree.xpath('//a[contains(@href, "artist:")]/text()')
        if illustrator_list:
            illustrator = illustrator_list[0].strip()

        # Evolution N-1
        evo_n1_list = tree.xpath('//p[@class="card-text-type"]/a[contains(@href, "name:")]/text()')
        if evo_n1_list:
            evo_n1 = evo_n1_list[0].strip()

        # Stage Evolution (Basic = 0, Stage X = X)
        stage_raw = tree.xpath('//p[@class="card-text-type"]/text()')
        for line in stage_raw:
            clean = line.strip()
            if "Stage" in clean:
                match = re.search(r"Stage\s+(\d+)", clean)
                if match:
                    stage_evo = match.group(1)
                    break
            elif "Basic" in clean:
                stage_evo = "0"
                break

        return subtype, hp, illustrator, evo_n1, stage_evo
    except Exception as e:
        log(f"⚠️ Erreur scraping {card_set}_{card_number} : {e}")
        return None, None, None, None, None

def enrich_dwh_cards():
    log("🔧 Connexion à la base de données")
    try:
        with psycopg2.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                # 💣 DROP + CREATE de dwh_cards
                log("💣 DROP + CREATE de dwh_cards")
                cur.execute("DROP TABLE IF EXISTS public.dwh_cards")
                cur.execute("""
                    CREATE TABLE public.dwh_cards (
                        card_id TEXT PRIMARY KEY,
                        card_name TEXT,
                        card_set TEXT,
                        card_number TEXT,
                        card_type TEXT,
                        card_subtype TEXT,
                        card_hp INT,
                        card_illustrator TEXT,
                        evolution_n1 TEXT,
                        stage_evo TEXT,
                        card_url TEXT,
                        card_img_url TEXT
                    );
                """)
                conn.commit()
                log("✅ Table recréée avec colonnes ordonnées")

                # 📥 Insertion depuis JSON
                records = extract_card_data_from_json(json_folder)
                log(f"📥 Insertion de {len(records)} cartes depuis les JSON")

                for rec in records:
                    card_id, card_set, card_number, card_type, card_name, card_url = rec
                    card_img_url = f"https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket/{card_set}/{card_set}_{card_number.zfill(3)}_EN.webp"
                    cur.execute("""
                        INSERT INTO public.dwh_cards (
                            card_id, card_set, card_number, card_type, card_name, card_url, card_img_url
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (card_id) DO NOTHING;
                    """, (card_id, card_set, card_number, card_type, card_name, card_url, card_img_url))
                conn.commit()
                log("✅ Insertion JSON terminée")

                # 🔁 Scraping des colonnes manquantes
                cur.execute("""
                    SELECT card_id, card_set, card_number FROM public.dwh_cards
                    WHERE card_subtype IS NULL OR card_hp IS NULL OR card_illustrator IS NULL OR evolution_n1 IS NULL OR stage_evo IS NULL;
                """)
                rows = cur.fetchall()
                total = len(rows)
                log(f"🔁 Scraping de {total} cartes pour subtype, hp, illustrator, evolution, stage")

                for i, (card_id, card_set, card_number) in enumerate(rows, 1):
                    log(f"🔎 ({i}/{total}) {card_id}")
                    subtype, hp, illustrator, evo_n1, stage_evo = get_card_details(card_set, card_number)
                    cur.execute("""
                        UPDATE public.dwh_cards
                        SET card_subtype = %s,
                            card_hp = %s,
                            card_illustrator = %s,
                            evolution_n1 = %s,
                            stage_evo = %s
                        WHERE card_id = %s
                    """, (subtype, hp, illustrator, evo_n1, stage_evo, card_id))
                    log(f"✅ {card_id} → subtype: {subtype} | hp: {hp} | illustrator: {illustrator} | evo: {evo_n1} | stage: {stage_evo}")

            conn.commit()
            log("✅ Commit finalisé")
    except Exception as e:
        log(f"❌ Erreur enrichissement : {e}")

if __name__ == "__main__":
    log("🧠 Démarrage enrichissement dwh_cards (type+name depuis JSON, subtype+hp+illustrator+evo+stage depuis web)")
    enrich_dwh_cards()
