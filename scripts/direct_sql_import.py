import json
import psycopg2
import sys
from urllib.parse import urlparse

def direct_import(json_file, db_url):
    print(f"Reading {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Found {len(data)} records.")
    
    # Parse DB URL
    result = urlparse(db_url)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port or 5432

    print(f"Connecting to {hostname}...")
    conn = psycopg2.connect(
        database=database,
        user=username,
        password=password,
        host=hostname,
        port=port,
        sslmode='require'
    )
    cur = conn.cursor()

    print("Deleting existing records...")
    cur.execute("DELETE FROM scorecard_votingrecord;")
    
    print("Inserting records...")
    query = """
    INSERT INTO scorecard_votingrecord (id, senator_id, date, title, decision, source)
    VALUES (%s, %s, %s, %s, %s, %s);
    """
    
    records = []
    for entry in data:
        f = entry['fields']
        records.append((
            entry['pk'],
            f['senator'],
            f['date'],
            f['title'],
            f['decision'],
            f['source']
        ))
    
    # Use execute_batch for better performance
    from psycopg2.extras import execute_batch
    execute_batch(cur, query, records, page_size=100)
    
    conn.commit()
    print(f"Success! {len(records)} records imported.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    db_url = "postgresql://neondb_owner:npg_UAeBkERHhF24@ep-falling-wind-adz4ytm9-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    direct_import("voting_records_dump.json", db_url)
