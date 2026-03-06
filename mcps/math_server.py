from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Math Server")

@mcp.tool()
def addition(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def multiplication(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

@mcp.tool()
def subtraction(a: int, b: int) -> int:
    """Subtract b from a"""
    return a - b

@mcp.tool()
def division(a: int, b: int) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

if __name__ == "__main__":
    # Run with stdio transport (for LangGraph integration)
    mcp.run(transport="stdio")