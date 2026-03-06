from fastapi import FastAPI
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import datetime

app = FastAPI()

# ======================
# GOOGLE OAUTH CONFIG
# ======================
CLIENT_ID = ""
CLIENT_SECRET = ""
REFRESH_TOKEN = ""
TOKEN_URI = "https://oauth2.googleapis.com/token"

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)

# ======================
# MCP REQUEST SCHEMA
# ======================
class CalendarEvent(BaseModel):
    title: str
    start_time: str   # ISO format
    end_time: str
    attendees: list[str] = []

# ======================
# MCP TOOL
# ======================
@app.post("/mcp/create_calendar_event")
def create_calendar_event(data: CalendarEvent):
    service = get_calendar_service()
    print('MCP Server is running')
    event = {
        "summary": data.title,
        "start": {"dateTime": data.start_time},
        "end": {"dateTime": data.end_time},
        "attendees": [{"email": a} for a in data.attendees],
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return {
        "status": "success",
        "event_id": created_event.get("id"),
        "htmlLink": created_event.get("htmlLink")
    }