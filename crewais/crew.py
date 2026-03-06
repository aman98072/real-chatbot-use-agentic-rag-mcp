# crewai_weather_app.py
from dotenv import load_dotenv
import os
import json
import re
from typing import List, Dict, Any, Optional

# CrewAI imports
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# MCP imports
from mcps.mcp_config import init_mcp, mcp_manager
from mcps.mcp_client import create_calendar_event_via_mcp

load_dotenv()

# =====================
# LLM SETUP
# =====================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5
)

# =====================
# CUSTOM MCP TOOLS FOR CREWAI
# =====================

class WeatherTool(BaseTool):
    name: str = "Weather Information Tool"
    description: str = "Get current weather information for any city"
    
    def _run(self, city: str) -> str:
        """Get weather for a city"""
        if not mcp_manager.initialized:
            return "⚠️ Weather service not initialized"
        
        try:
            result = mcp_manager.use_tool("weather", "get_weather", city=city)
            return result
        except Exception as e:
            return f"Error fetching weather: {str(e)}"
    
    async def _arun(self, city: str) -> str:
        """Async version"""
        return self._run(city)

class MathTool(BaseTool):
    name: str = "Math Calculator Tool"
    description: str = "Perform mathematical calculations like addition, subtraction, multiplication, division, etc."
    
    def _run(self, operation: str, **kwargs) -> str:
        """Perform math operation"""
        if not mcp_manager.initialized:
            return "⚠️ Math service not initialized"
        
        try:
            if operation == "addition":
                return mcp_manager.use_tool("math", "addition", **kwargs)
            elif operation == "subtraction":
                return mcp_manager.use_tool("math", "subtraction", **kwargs)
            elif operation == "multiplication":
                return mcp_manager.use_tool("math", "multiplication", **kwargs)
            elif operation == "division":
                return mcp_manager.use_tool("math", "division", **kwargs)
            else:
                return f"Unknown operation: {operation}"
        except Exception as e:
            return f"Error in math calculation: {str(e)}"

class CalendarTool(BaseTool):
    name: str = "Calendar Meeting Tool"
    description: str = "Schedule meetings in Google Calendar"
    
    def _run() -> str:
        """Schedule a meeting"""
        try:
            result = create_calendar_event_via_mcp(
                title="User Support / Loan Discussion Call",
                start_time="2026-03-05T10:00:00+05:30",
                end_time="2026-03-05T10:30:00+05:30",
                attendees=["aman98072@gmail.com"]
            )
            return f"Meeting scheduled successfully: {result}"
        except Exception as e:
            return f"Error scheduling meeting: {str(e)}"


class SupervisorAgent:
    """Determines which agents to call based on user input"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def analyze(self, user_input: str) -> Dict[str, Any]:
        """Analyze user input and return routing decision"""
        
        prompt = f"""
        You are a supervisor AI. Analyze the user query and decide:
        1. Which agents are needed
        2. Extract city name if weather is mentioned
        3. Return in JSON format

        Options:
        - retention: anger, frustration, complaint, dissatisfaction
        - loan: loan amount, EMI, eligibility, interest
        - rag: company policy, process, factual info
        - weather: weather information, temperature, forecast, rain, humidity
        - math: mathematical calculations, equations
        - meeting: schedule meeting, appointment, call

        User query: {user_input}

        Return JSON:
        {{
            "city": "extracted_city_name_or_empty",
            "agents": ["agent1", "agent2", ...],
            "meeting_details": {{
                "needed": true/false,
                "title": "meeting title if needed"
            }}
        }}

        Example for "Delhi ka weather batao":
        {{
            "city": "Delhi",
            "agents": ["weather"],
            "meeting_details": {{"needed": false}}
        }}

        Example for "gussa aa raha hai aur loan chahiye":
        {{
            "city": "",
            "agents": ["retention", "loan"],
            "meeting_details": {{"needed": false}}
        }}
        """
        
        response = self.llm.invoke(prompt).content
        print(f"🔍 Supervisor analysis: {response}")
        
        try:
            # Extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Default fallback
        return {
            "city": "",
            "agents": ["rag"],
            "meeting_details": {"needed": False}
        }


# =====================
# CREATE CREWAI AGENTS
# =====================

def create_agents():
    """Create all CrewAI agents"""
    
    # Retention Agent
    retention_agent = Agent(
        role='Customer Retention Specialist',
        goal='Handle customer complaints with empathy and find solutions',
        backstory="""You are a customer service expert who excels at 
        handling frustrated customers. You listen empathetically and 
        provide satisfactory solutions to retain customers.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # RAG Agent (General Information)
    rag_agent = Agent(
        role='Company Policy Expert',
        goal='Provide accurate information about company policies',
        backstory="""You are an HR expert who knows all company policies, 
        procedures, and guidelines. You provide accurate and helpful 
        information to employees and customers.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # Weather Agent
    weather_agent = Agent(
        role='Weather Specialist',
        goal='Provide accurate weather information for any city',
        backstory="""You are an expert meteorologist who can provide 
        detailed weather information including temperature, conditions, 
        humidity, and forecasts for any city worldwide.""",
        tools=[WeatherTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # Math Agent
    math_agent = Agent(
        role='Mathematics Expert',
        goal='Perform accurate mathematical calculations',
        backstory="""You are a mathematics professor who excels at 
        calculations including EMI, interest, and basic arithmetic.""",
        tools=[MathTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # Loan Agent
    loan_agent = Agent(
        role='Loan Specialist',
        goal='Provide accurate loan information and guidance',
        backstory="""You are a senior loan officer with expertise in 
        personal loans, home loans, and business loans. You explain 
        eligibility, interest rates, and processes clearly.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # Meeting Agent
    meeting_agent = Agent(
        role='Meeting Scheduler',
        goal='Schedule meetings efficiently and confirm details',
        backstory="""You are an executive assistant who excels at 
        scheduling meetings, managing calendars, and sending confirmations.""",
        tools=[CalendarTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # EMI Agent (Specialized)
    emi_agent = Agent(
        role='EMI Calculator Specialist',
        goal='Calculate accurate EMIs for loans',
        backstory="""You are a financial analyst who specializes in 
        EMI calculations, helping customers understand their monthly 
        payments for different loan amounts and tenures.""",
        tools=[MathTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # Status Agent
    status_agent = Agent(
        role='Loan Status Tracker',
        goal='Provide accurate loan application status',
        backstory="""You are a loan processing officer who tracks 
        application status and provides updates to customers.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    return {
        "weather": weather_agent,
        "math": math_agent,
        "loan": loan_agent,
        "retention": retention_agent,
        "rag": rag_agent,
        "meeting": meeting_agent,
        "emi": emi_agent,
        "status": status_agent
    }

# =====================
# TASK CREATION FUNCTIONS
# =====================

def create_weather_task(agent, city: str):
    """Create weather task"""
    return Task(
        description=f"Get current weather information for {city}. Include temperature, conditions, and humidity.",
        agent=agent,
        expected_output=f"Detailed weather report for {city}"
    )

def create_math_task(agent, calculation: str):
    """Create math task"""
    return Task(
        description=f"Perform this calculation: {calculation}",
        agent=agent,
        expected_output="Calculation result"
    )

def create_loan_task(agent, query: str):
    """Create loan task"""
    return Task(
        description=f"Provide loan information for: {query}. Include eligibility, interest rates, and process.",
        agent=agent,
        expected_output="Loan information and guidance"
    )

def create_retention_task(agent, query: str):
    """Create retention task"""
    return Task(
        description=f"Handle this customer complaint with empathy: {query}. Provide a helpful response.",
        agent=agent,
        expected_output="Empathetic response with solution"
    )

def create_rag_task(agent, query: str):
    """Create RAG task"""
    return Task(
        description=f"Provide company policy information for: {query}",
        agent=agent,
        expected_output="Policy information"
    )

def create_meeting_task(agent, title: str = "Customer Meeting"):
    """Create meeting task"""
    return Task(
        description=f"Schedule a meeting with title: {title}. Use default time if not specified.",
        agent=agent,
        expected_output="Meeting confirmation"
    )

def create_emi_task(agent, amount: float = 500000, rate: float = 8.5, tenure: int = 15):
    """Create EMI task"""
    return Task(
        description=f"Calculate EMI for loan amount: {amount}, rate: {rate}%, tenure: {tenure} years",
        agent=agent,
        expected_output="EMI calculation"
    )

def create_status_task(agent, application_id: str = "LOAN123"):
    """Create status task"""
    return Task(
        description=f"Check status for loan application: {application_id}",
        agent=agent,
        expected_output="Application status"
    )

# =====================
# MAIN CREW EXECUTION
# =====================

def run_crewai(message: str) -> str:
    """Main function to run CrewAI with dynamic task creation"""
    
    # Initialize MCP
    init_mcp()
    
    # Create agents
    agents = create_agents()
    
    # Analyze with supervisor
    supervisor = SupervisorAgent(llm)
    analysis = supervisor.analyze(message)
    
    city = analysis.get("city", "")
    required_agents = analysis.get("agents", ["rag"])
    meeting_needed = analysis.get("meeting_details", {}).get("needed", False)
    
    print(f"📋 Required agents: {required_agents}")
    print(f"📍 City: {city}")
    
    # Create tasks based on required agents
    tasks = []
    
    for agent_name in required_agents:
        if agent_name == "weather" and city:
            tasks.append(create_weather_task(agents["weather"], city))
        
        elif agent_name == "math":
            tasks.append(create_math_task(agents["math"], message))
        
        elif agent_name == "loan":
            tasks.append(create_loan_task(agents["loan"], message))
            # Automatically add EMI and status for loan
            tasks.append(create_emi_task(agents["emi"]))
            tasks.append(create_status_task(agents["status"]))
            tasks.append(create_meeting_task(agents["meeting"]))
        
        elif agent_name == "retention":
            tasks.append(create_retention_task(agents["retention"], message))
        
        elif agent_name == "rag":
            tasks.append(create_rag_task(agents["rag"], message))
            
    
    # If no tasks, add default RAG task
    if not tasks:
        tasks.append(create_rag_task(agents["rag"], message))
    
    # Create crew with sequential process
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=True,
        process=Process.sequential  # Tasks execute in order
    )
    
    # Execute crew
    print("\n🚀 Starting CrewAI execution...")
    result = crew.kickoff()
    
    print(f"\n✅ CrewAI execution complete")
    
    return str(result)

