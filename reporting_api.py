from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# Database connection details
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
        options=f"-c search_path={DB_SCHEMA}",
        cursor_factory=RealDictCursor
    )
    return conn

class TopPath(BaseModel):
    path: str
    views: int

class SiteStats(BaseModel):
    site_id: str
    date: str
    total_views: int
    unique_users: int
    top_paths: List[TopPath]

@app.get("/stats", response_model=SiteStats)
async def get_site_stats(site_id: str, date: date = Query(...)):
    """
    Retrieves and aggregates website analytics for a given site and date.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:

            date_str = date.isoformat()

        # Query for total views
            cur.execute(
                "SELECT COUNT(*) as total_views FROM website_events WHERE site_id = %s AND DATE(timestamp) = %s",
                (site_id, date_str)
            )
            total_views_result = cur.fetchone()
            total_views = total_views_result['total_views'] if total_views_result else 0

        # Query for unique users
            cur.execute(
                "SELECT COUNT(DISTINCT user_id) as unique_users FROM website_events WHERE site_id = %s AND DATE(timestamp) = %s",
                (site_id, date_str)
            )
            unique_users_result = cur.fetchone()
            unique_users = unique_users_result['unique_users'] if unique_users_result else 0

        # Query for top paths
            cur.execute(
                """
                SELECT path, COUNT(*) as views
                FROM website_events
                WHERE site_id = %s AND DATE(timestamp) = %s
                GROUP BY path
                ORDER BY views DESC
                LIMIT 10;
                """,
                (site_id, date_str)
            )
            top_paths_result = cur.fetchall()
            top_paths = [TopPath(**row) for row in top_paths_result]

            cur.close()
            conn.close()

        return SiteStats(
            site_id=site_id,
            date=date_str,
            total_views=total_views,
            unique_users=unique_users,
            top_paths=top_paths
        )
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)