import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_tables():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT")
        )
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = [row[0] for row in cur.fetchall()]
        print(f"📊 Found tables: {tables}")
        if 'file_cache' in tables:
            print("🚀 'file_cache' table correctly exists in PostgreSQL!")
        else:
            print("❌ 'file_cache' table is missing.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_tables()
