from celery import Celery
import json
import psycopg2
from datetime import datetime,time

import redis

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

DB_HOST = "127.0.0.1"
DB_PORT="5432"
DB_NAME = "website-analytics"
DB_USER = "postgres"
DB_PASS = "Kgf@2018"
DB_SCHEMA = "analytics"

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        options=f"-c search_path={DB_SCHEMA}"
    )
    return conn

@celery_app.task(name='processor.process_event')
def process_event(event_json: str):
    """
    Parses an event from JSON and inserts it into the PostgreSQL database.
    """
    try:
        event_data = json.loads(event_json)

        event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])

        conn = get_db_connection()
        with conn,conn.cursor() as cur:

            insert_query = """
            INSERT INTO website_events (site_id, event_type, path, user_id, "timestamp")
            VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(insert_query, (
                event_data['site_id'],
                event_data['event_type'],
                event_data['path'],
                event_data['user_id'],
                event_data['timestamp']
            ))
            conn.commit()
            cur.close()
            conn.close()
        print(f"Processed event for site: {event_data['site_id']}")
    except (Exception, psycopg2.Error) as error:
        print(f"Error processing event: {error}")


def main():
    """
    Continuously pulls events from the Redis queue and dispatches them to Celery workers.
    """
    print("Starting processor worker...")
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    while True:
        # Use BRPOP for a blocking pop, which is more efficient than polling
        try:
            _, event_json = redis_client.brpop('events_queue')
            if event_json:
                process_event.delay(event_json)
        except redis.exceptions.ConnectionError as e:
            print(f"Could not connect to Redis, retrying... Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()