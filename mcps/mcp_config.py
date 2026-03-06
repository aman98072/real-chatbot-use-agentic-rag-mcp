# mcp_config.py
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import traceback
import atexit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MATH_SERVER_PATH = os.path.join(BASE_DIR, "math_server.py")
WEATHER_SERVER_PATH = os.path.join(BASE_DIR, "weather_server.py")

def debug_log(msg):
    print(f"[MCP] {msg}", file=sys.stderr, flush=True)

debug_log(f"Math server: {MATH_SERVER_PATH}")
debug_log(f"Weather server: {WEATHER_SERVER_PATH}")
debug_log(f"Files exist? Math: {os.path.exists(MATH_SERVER_PATH)}, Weather: {os.path.exists(WEATHER_SERVER_PATH)}")

MCP_SERVER_CONFIG = {
    "math": {
        "command": "python",
        "args": [MATH_SERVER_PATH],
        "transport": "stdio",
    },
    "weather": {
        "command": "python",
        "args": [WEATHER_SERVER_PATH],
        "transport": "stdio",
    },
}

class MCPClientManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._client = None
                cls._instance._tools = []
                cls._instance._startup_complete = False
            return cls._instance
    
    def __init__(self):
        # Skip if already initialized
        if hasattr(self, '_init_done'):
            return
        self._init_done = True
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._init_thread = None
        self._init_event = threading.Event()
    
    def start_initialization(self):
        """Start MCP initialization in background"""
        with self._lock:
            if self._initialized or self._init_thread:
                return True
            
            debug_log("Starting MCP initialization in background...")
            self._init_thread = threading.Thread(target=self._initialize_sync, daemon=True)
            self._init_thread.start()
            return True
    
    def _initialize_sync(self):
        """Initialize MCP in background thread"""
        try:
            debug_log("Initializing MCP client in thread...")
            
            # Create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create client
            self._client = MultiServerMCPClient(MCP_SERVER_CONFIG)
            debug_log("MultiServerMCPClient created")
            
            # Get tools
            self._tools = loop.run_until_complete(self._client.get_tools())
            
            if self._tools:
                debug_log(f"Loaded MCP tools: {[t.name for t in self._tools]}")
                self._initialized = True
                self._startup_complete = True
            else:
                debug_log("No tools loaded - check if servers are running")
                self._initialized = False
            
            loop.close()
            
        except Exception as e:
            debug_log(f"Initialization error: {e}")
            traceback.print_exc(file=sys.stderr)
            self._initialized = False
        finally:
            self._init_event.set()
    
    def wait_for_initialization(self, timeout=5):
        """Wait for initialization to complete"""
        if self._initialized:
            return True
        return self._init_event.wait(timeout)
    
    @property
    def tools(self):
        return self._tools
    
    @property
    def initialized(self):
        return self._initialized


    def get_tools_by_server(self, server_name: str):
        """Get tools from specific MCP server - FIXED VERSION"""
        if not self._initialized or not self._tools:
            print(f'⚠️ MCP not initialized or no tools')
            return []
        
        print(f'🔍 Searching tools for server: {server_name}')
        print(f'📋 All tools: {[t.name for t in self._tools]}')
        
        # Method 1: Startswith (exact match)
        exact_matches = [t for t in self._tools if t.name.startswith(server_name)]
        if exact_matches:
            return exact_matches
        
        # Method 2: Contains (partial match)
        partial_matches = [t for t in self._tools if server_name.lower() in t.name.lower()]
        if partial_matches:
            return partial_matches
        
        
        print(f'❌ No tools found for server: {server_name}')
        return []

    
    def use_tool(self, server_name: str, tool_name: str, **kwargs) -> str:
        """Use a specific MCP tool"""
        if not self.wait_for_initialization(timeout=5):
            return "⚠️ MCP client still initializing. Please try again."
        
        try:
            # Run in executor
            future = self._executor.submit(self._use_tool_sync, server_name, tool_name, kwargs)
            return future.result(timeout=10)
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _use_tool_sync(self, server_name: str, tool_name: str, kwargs: dict) -> str:
        """Use tool synchronously"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            server_tools = self.get_tools_by_server(server_name)
            for tool in server_tools:
                if tool_name in tool.name or tool.name == tool_name:
                    result = loop.run_until_complete(tool.ainvoke(kwargs))
                    return str(result)
            return f"⚠️ Tool {tool_name} not found"
        finally:
            loop.close()
    
    def cleanup(self):
        """Cleanup resources"""
        debug_log("Cleaning up MCP...")
        self._executor.shutdown(wait=False)

# Global instance (singleton)
mcp_manager = MCPClientManager()

def init_mcp():
    """Initialize MCP (non-blocking)"""
    debug_log("init_mcp called")
    return mcp_manager.start_initialization()

def is_mcp_ready():
    """Check if MCP is ready"""
    return mcp_manager.initialized

# Auto-start initialization
debug_log("Auto-starting MCP initialization...")
init_mcp()

# Register cleanup
atexit.register(lambda: mcp_manager.cleanup())