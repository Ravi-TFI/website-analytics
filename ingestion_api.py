from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import redis
import json
from datetime import datetime

app = FastAPI()

try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("Connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    redis_client = None

class Event(BaseModel):
    site_id: str
    event_type: str
    path: str
    user_id: str
    timestamp: datetime

@app.post("/event", status_code=status.HTTP_202_ACCEPTED)
async def capture_event(event: Event):
    """
    Receives an analytics event, validates it, and places it into an
    asynchronous processing queue (Redis).
    """
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to the processing queue."
        )

    try:
        event_dict = event.model_dump()
        event_dict['timestamp'] = event_dict['timestamp'].isoformat()
        event_json = json.dumps(event_dict)

        redis_client.lpush('events_queue', event_json)

        return {"message": "Event accepted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue event: {e}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)