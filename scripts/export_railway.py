import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# Charger les variables .env
load_dotenv(".env")

# Connexion à Railway
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

# Export CSV + Parquet
def export_table(table_name, output_dir="exports"):
    os.makedirs(output_dir, exist_ok=True)

    try:
        with get_connection() as conn:
            df = pd.read_sql(f"SELECT * FROM public.{table_name}", conn)

            csv_path = os.path.join(output_dir, f"{table_name}.csv")


            df.to_csv(csv_path, index=False)


            print(f"[✅] {table_name} exportée ({len(df)} lignes)")
            print(f"     ├─ CSV     : {csv_path}")


    except Exception as e:
        print(f"[❌] Erreur export {table_name} : {e}")

if __name__ == "__main__":
    tables = ["wrk_decklists"]  # adapte si tu veux
    for table in tables:
        export_table(table)
