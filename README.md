# Website Analytics Service

This project is a high-performance backend system designed to capture and analyze website analytics events. It features a decoupled architecture with three distinct services to handle high-volume data ingestion with low latency.

---

### Architecture Decision

The system is built on a producer-consumer pattern to ensure the event ingestion endpoint is extremely fast, as required.

*   **Service 1: Ingestion API (The Producer)**
    *   A lightweight FastAPI application that receives events via a `POST` request.
    *   Its only job is to perform basic validation and immediately push the event into a message queue.

*   **Service 2: The Queue (The Buffer)**
    *   **Redis** was chosen as the message broker. Its in-memory nature provides the extremely low latency needed for a rapid handoff from the ingestion API. It acts as a resilient buffer, absorbing spikes in traffic and decoupling the ingestion service from the slower processing and database-writing service.

*   **Service 3: The Processor (The Consumer)**
    *   A background worker managed by **Celery**. Celery is a robust and mature task queue system that integrates seamlessly with Redis.
    *   The processor pulls events from the Redis queue, processes them, and writes them to the database. This "heavy lifting" is done asynchronously, so it never blocks the client-facing Ingestion API.

*   **Service 4: The Reporting API**
    *   A separate FastAPI application that provides aggregated analytics by querying the database.

This asynchronous architecture ensures scalability and high performance for the ingestion endpoint, as the client does not have to wait for a database write to complete.

---

### Database Schema

The application uses a PostgreSQL database with a single table, `website_events`, located in a dedicated schema named `analytics`.

*   **Schema:** `analytics`
*   **Table:** `website_events`

| Column      | Type        | Description                                  |
|-------------|-------------|----------------------------------------------|
| `id`        | `SERIAL`    | Primary Key, auto-incrementing integer.      |
| `site_id`   | `VARCHAR`   | The identifier of the website being tracked. |
| `event_type`| `VARCHAR`   | The type of event (e.g., 'page_view', 'click'). |
| `path`      | `VARCHAR`   | The URL path where the event occurred.       |
| `user_id`   | `VARCHAR`   | The identifier for the user.                 |
| `timestamp` | `TIMESTAMPTZ`| The exact time of the event (with timezone). |

---

### Setup Instructions

Follow these steps to build and run the entire system.

**Prerequisites:**
*   Python 3.10+
*   PostgreSQL Server
*   Redis Server
*   Git

**1. Clone the Repository:**
```bash
git clone https://github.com/Ravi-TFI/website-analytics.git
cd website-analytics
```

**2. Create a Virtual Environment and Install Dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```
*(Note: You will need to create a `requirements.txt` file by running `pip freeze > requirements.txt`)*

**3. Configure PostgreSQL:**
*   Create a database and a user.
*   Run the following SQL to create the schema and table:
    ```sql
    CREATE SCHEMA analytics;
    CREATE TABLE analytics.website_events (
        id SERIAL PRIMARY KEY,
        site_id VARCHAR(255) NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        path VARCHAR(2048) NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        "timestamp" TIMESTAMPTZ NOT NULL
    );
    ```

**4. Update Configuration:**
In `processor.py` and `reporting_api.py`, update the database connection variables with your credentials:
```python
DB_NAME = "your_db_name"
DB_USER = "your_db_user"
DB_PASS = "your_db_password"
DB_SCHEMA = "analytics"
```

**5. Run the Services:**
Open four separate terminals and run the following commands, one in each terminal.

*   **Terminal 1: Ingestion API**
    ```bash
    uvicorn ingestion_api:app --reload
    ```

*   **Terminal 2: Reporting API**
    ```bash
    uvicorn reporting_api:app --reload --port 8001
    ```

*   **Terminal 3: Celery Worker** (For Windows, `-P gevent` is required)
    ```bash
    celery -A processor.celery_app worker --loglevel=info -P gevent
    ```

*   **Terminal 4: Processor (Queue Poller)**
    ```bash
    python processor.py
    ```

---

### API Usage

**1. Send an Analytics Event:**
Use `curl` to send a `POST` request to the `/event` endpoint. The server will respond immediately with a `202 Accepted` status.

```bash
curl -X POST "http://localhost:8000/event" \
-H "Content-Type: application/json" \
-d '{
  "site_id": "site-abc-123",
  "event_type": "page_view",
  "path": "/pricing",
  "user_id": "user-xyz-789",
  "timestamp": "2025-11-16T10:00:00Z"
}'
```

**2. Retrieve Aggregated Statistics:**
Use `curl` to send a `GET` request to the `/stats` endpoint with `site_id` and `date` as query parameters.

```bash
curl "http://localhost:8001/stats?site_id=site-abc-123&date=2025-11-16"
```

**Example Success Response:**
```json
{
  "site_id": "site-abc-123",
  "date": "2025-11-16",
  "total_views": 1,
  "unique_users": 1,
  "top_paths": [
    {
      "path": "/pricing",
      "views": 1
    }
  ]
}
```
