from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")


@mcp.tool()
async def greet(name: str) -> str:
    """Greet someone

    Args:
        name (str): The name to greet
    """
    return "Hello, " + name


if __name__ == "__main__":
    mcp.run()
