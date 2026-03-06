import requests

MCP_SERVER_URL = "http://127.0.0.1:9000/mcp/create_calendar_event"

def create_calendar_event_via_mcp(
    title: str,
    start_time: str,
    end_time: str,
    attendees: list[str]
):
    print(f"Calling MCP to create calendar event: {title} at {start_time}")
    payload = {
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "attendees": attendees
    }

    response = requests.post(MCP_SERVER_URL, json=payload, timeout=10)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"MCP Error: {response.text}")