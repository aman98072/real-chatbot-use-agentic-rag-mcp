

from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from mcps.mcp_client import create_calendar_event_via_mcp
from mcps.mcp_config import init_mcp, mcp_manager
import json
import re

load_dotenv()

# =====================
# STATE
# =====================
class ChatState(TypedDict):
    user_input: str
    routes: List[str]        # which agents to call (ordered)
    responses: List[str]     # responses from agents
    current_step: int        # pointer for sequential execution
    mcp_results: Dict[str, Any]  # Store MCP tool results
    detected_city: str  # Add this field for weather city


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5
)

# =====================
# SUPERVISOR AGENT
# =====================
def supervisor_agent(state: ChatState) -> ChatState:
    """
    Decide which agents should be called (multiple allowed).
    """

    prompt = f"""
        You are a supervisor AI.

        Analyze the user query and decide which of the following are REQUIRED.
        Return a JSON response with city and routes.

        Options:
        - retention → anger, frustration, complaint, dissatisfaction
        - loan → loan amount, EMI, eligibility, interest
        - rag → company policy, process, factual info
        - weather → weather information, temperature, forecast, rain, humidity (e.g., "Delhi ka weather", "rain in Mumbai", "temperature in London")
        - math → mathematical calculations, addition, subtraction, multiplication, division, equations (e.g., What is 25% of 400?, Solve 2x + 3 = 7, Calculate the area of a circle with radius 5)

        Rules:
        - If user is angry or emotional → retention MUST be included FIRST
        - Multiple options are allowed
        - If user asks about weather, extract the city name

        User query:
        {state["user_input"]}

        Return example:
        Return format (valid JSON):
        {{
            "city": "extracted_city_name_or_empty_string",
            "routes": ["retention", "loan", "rag", "weather", "math"]  # comma-separated list in correct order
        }}

        Example 1 (weather query):
        {{
            "city": "Delhi",
            "routes": ["weather", "rag"]
        }}

        Example 2 (math + loan):
        {{
            "city": "",
            "routes": ["math", "loan", "rag"]
        }}

        Example 3 (emotional + weather):
        {{
            "city": "Mumbai",
            "routes": ["retention", "weather", "rag"]
        }}
    """

    routes_raw = llm.invoke(prompt).content.lower()
    print(f"Supervisor raw response: {routes_raw}")

    routes = []
    city = ""
    try:
        # Try to extract JSON from response (in case LLM adds extra text)
        json_match = re.search(r'\{.*\}', routes_raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            city = data.get("city", "")
            routes = data.get("routes", [])
            print(f"✅ Parsed city: {city}")
            print(f"✅ Parsed routes: {routes}")
        else:
            print("⚠️ No JSON found in response")
            routes = ["rag"]
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        # Fallback: try to parse as comma-separated list
        routes = [r.strip() for r in routes_raw.split(",") if r.strip()]
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        routes = ["rag"]
    
    # Validate routes
    valid = {"rag", "loan", "retention", "weather", "math"}
    
    # If routes is a list, validate each item
    if isinstance(routes, list):
        routes = [r for r in routes if r in valid]
    # If routes is a string, split and validate
    elif isinstance(routes, str):
        routes = [r.strip() for r in routes.split(",") if r.strip() in valid]
    else:
        routes = []
    
    print(f"✅ Validated routes: {routes}")
    
    if not routes:
        routes = ["rag"]  # safe default
        print("⚠️ No valid routes found, using default: ['rag']")

    # ==================== STORE CITY IN STATE ====================
    # You need to add 'detected_city' to your ChatState first
    # For now, we'll just print it
    if city:
        print(f"📍 Detected city: {city}")
        # If you add detected_city to ChatState, you can store it like:
        state['detected_city'] = city

    return {
        "user_input": state["user_input"],
        "routes": routes,
        "responses": [],
        "current_step": 0,
        "detected_city": city  # Add this if you add to ChatState
    }

# =====================
# RETENTION AGENT
# =====================
def retention_agent(state: ChatState) -> ChatState:
    response = (
        "Mujhe afsos hai ki aap pareshaan hain. "
        "Main aapki madad karna chahta hoon. "
        "Pehle hum aapki problem samajh lete hain aur phir solution nikaalte hain."
    )

    state["responses"].append(response)
    state["current_step"] += 1
    return state

# =====================
# LOAN AGENT
# =====================
def loan_agent(state: ChatState) -> ChatState:
    response = (
        "5 lakh ke loan ke liye eligibility income, credit score "
        "aur repayment capacity par depend karti hai. "
        "Main aapko process aur requirements samjha sakta hoon."
    )

    state["responses"].append(response)
    state["current_step"] += 1
    return state


def emi_agent(state: ChatState) -> ChatState:
    response = (
        "5 lakh ke loan par EMI 32000 per month ke aas paas, 15 saal ke tenure pe. "
    )

    state["responses"].append(response)
    state["current_step"] += 1
    return state


def status_agent(state: ChatState) -> ChatState:
    response = (
        "Aapka loan application process mein hai. Aapko email ke through updates milte rahenge. "
        "Agar aapko koi problem ho, toh hum aapki madad karne ke liye tayyar hain."
    )

    state["responses"].append(response)
    state["current_step"] += 1
    return state


def schedule_meeting_agent(state: ChatState) -> ChatState:
    """
    This agent:
    1. Confirms meeting intent
    2. Calls MCP to create Google Calendar event
    """

    # ------------- USER-FACING RESPONSE -------------
    response = (
        "Main aapke liye meeting schedule kar raha hoon. "
        "Kal subah 10 baje ki meeting confirm kar di gayi hai."
    )

    state["responses"].append(response)

    # ------------- MCP CALL (ACTION LAYER) -------------
    # NOTE: In real flow, date/time comes from user confirmation
    try:
        mcp_result = create_calendar_event_via_mcp(
            title="User Support / Loan Discussion Call",
            start_time="2026-03-05T10:00:00+05:30",
            end_time="2026-03-05T10:30:00+05:30",
            attendees=["aman98072@gmail.com"]
        )

        # Optional: log MCP result (NOT shown to user)
        state["responses"].append(
            "📅 Meeting successfully added to calendar.", mcp_result
        )

    except Exception as e:
        # MCP failure should not crash conversation
        state["responses"].append(
            "⚠️ Meeting schedule karne me thodi dikkat aayi. "
            "Hum aapko manually confirm kar denge."
        )

    # ------------- MOVE TO NEXT STEP -------------
    state["current_step"] += 1
    return state


# =====================
# RAG AGENT
# =====================
def rag_agent(state: ChatState) -> ChatState:
    response = (
        "Company policy ke according, loan application online ya branch ke through hoti hai. "
        "Documents jaise ID proof, income proof aur bank statements required hote hain."
    )

    state["responses"].append(response)
    state["current_step"] += 1
    return state


# =====================
# WEATHER AGENT
# =====================
def weather_agent(state: ChatState) -> ChatState:
    # Pehle detected_city ko state se nikaalo (hamesha karo, if block ke bahar)
    detected_city = state.get('detected_city', '')
    
    # Default city agar kuch nahi mila
    if not detected_city:
        user_input = state["user_input"].lower()
        cities = ["delhi", "mumbai", "bangalore", "chennai", "kolkata", 
                  "london", "new york", "tokyo", "paris", "sydney"]
        
        for city in cities:
            if city in user_input:
                detected_city = city
                break
        
        # Agar ab bhi nahi mila to default city do
        if not detected_city:
            detected_city = "Delhi"
    
    print(f'📍 detected_city : {detected_city}')
    
    weather_result = "Weather information not available"
    
    # Call MCP weather tools
    if mcp_manager.initialized:
        try:
            weather_result = mcp_manager.use_tool(
                "weather", "get_weather",
                city=detected_city
            )
            print(f'🌤️ weather_result : {weather_result}')
            state["mcp_results"]["current_weather"] = weather_result
        except Exception as e:
            print(f"❌ Error calling weather tool: {e}")
            weather_result = f"Error fetching weather: {str(e)}"
    else:
        weather_result = "⚠️ MCP client not initialized. Please check weather server."
    
    # Prepare response (ye ab hamesha chalega)
    response_parts = []
    response_parts.append(f"🌤️ **Weather Information for {detected_city.title()}**")
    response_parts.append("")
    response_parts.append(weather_result)
    response = "\n".join(response_parts)
    
    state["responses"].append(response)
    state["current_step"] += 1
    return state


# =====================
# ROUTER (SEQUENTIAL)
# =====================
def next_agent(state: ChatState) -> str:
    """
    Decide next agent based on routes list and current_step
    """
    if state["current_step"] >= len(state["routes"]):
        return END

    return state["routes"][state["current_step"]]

# =====================
# LANGGRAPH
# =====================
graph = StateGraph(ChatState)

graph.add_node("supervisor", supervisor_agent)
graph.add_node("retention", retention_agent)
graph.add_node("loan", loan_agent)
graph.add_node("rag", rag_agent)
graph.add_node("emi_agent", emi_agent)
graph.add_node("status_agent", status_agent)
graph.add_node("schedule_meeting_agent", schedule_meeting_agent)
graph.add_node("weather", weather_agent)
graph.add_edge("loan", "emi_agent")
graph.add_edge("emi_agent", "status_agent")
graph.add_edge("status_agent", "schedule_meeting_agent")


graph.set_entry_point("supervisor")

graph.add_conditional_edges(
    "supervisor",
    next_agent,
    {
        "retention": "retention",
        "loan": "loan",
        "rag": "rag",
        "weather": "weather",
        END: END
    }
)

graph.add_conditional_edges(
    "retention",
    next_agent,
    {
        "loan": "loan",
        "rag": "rag",
        "weather": "weather",
        END: END
    }
)

graph.add_conditional_edges(
    "loan",
    next_agent,
    {
        "rag": "rag",
        "weather": "weather",
        END: END
    }
)

graph.add_conditional_edges(
    "weather",
    next_agent,
    {
        "rag": "rag",
        "loan": "loan",
        "retention": "retention",
        END: END
    }
)

graph.add_edge("rag", END)

chat_graph = graph.compile()

# =====================
# PUBLIC FUNCTION
# =====================
def run_langgraph(message: str) -> str:
    result = chat_graph.invoke({
        "user_input": message,
        "routes": [],
        "responses": [],
        "current_step": 0,
        "mcp_results": {}
    })

    # Add MCP results summary
    if result.get("mcp_results"):
        mcp_summary = "\n\n📊 MCP Operations Summary:\n"
        for server, res in result["mcp_results"].items():
            if res and "Error" not in res:
                mcp_summary += f"- {server}: ✅ Success\n"
        result["responses"].append(mcp_summary)
    
    return "\n\n".join(result["responses"])
