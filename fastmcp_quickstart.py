"""
FastMCP quickstart example.

Run from the repository root:
    uv run examples/snippets/servers/fastmcp_quickstart.py
"""

from mcp.server.fastmcp import FastMCP
import os
import subprocess
import time
from typing import Optional

# Create an MCP server
mcp = FastMCP("Recipe Recall", json_response=True)

# AI Sticky notes
RECIPE_FILE = "recipes.txt"
def ensure_file():
    if not os.path.exists(RECIPE_FILE):
        with open(RECIPE_FILE, "w") as f:
            f.write("")

@mcp.tool()

def add_note(message: str) -> str:
    """
    Saves a recipe to the specified recipe file.
    Args:
    message (str): The content of the recipe to be saved.
    Returns:
    str: A confirmation message indicating the recipe was saved.
    Description:
    This function appends the provided message to the recipes file (RECIPE_FILE),
    ensuring the file exists before writing. The recipe is stored with a newline
    character at the end.
    """
    ensure_file()
    with open(RECIPE_FILE, "a") as f:
        f.write(message + "\n")
    return "Note saved."

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def search_recipes(keyword: str) -> str:
    """Find the ingredients for a given meal search term
    Args:
        keyword (str): The name of a single recipe to search.
    Returns:
        str: The ingredients from the recipe.
    """
    # Attempt to run the local scraper script and return its stdout.
    # Use subprocess.run with a timeout, retries and clear error handling so
    # the MCP tool doesn't fail silently or return an integer exit code.
    script_name = "bbcgoodfood_scraper_yolo.py"
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        # fallback to script in CWD
        script_path = script_name

    max_retries = 2
    timeout_seconds = 30
    backoff = 1.0

    for attempt in range(1, max_retries + 2):
        try:
            proc = subprocess.run(
                ["python", script_path, keyword],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=True,
            )
            output = proc.stdout.strip()
            # Optionally save to the recipes file for recall
            ensure_file()
            with open(RECIPE_FILE, "a", encoding="utf-8") as f:
                f.write(output + "\n")
            return output or "(no output)"

        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            stdout = (e.stdout or "").strip()
            msg = f"Script failed (exit {e.returncode}). stderr: {stderr!s} stdout: {stdout!s}"
            # don't retry for script errors
            return msg
        except subprocess.TimeoutExpired:
            if attempt > max_retries:
                return f"Error: scraper timed out after {timeout_seconds}s (attempt {attempt})"
            time.sleep(backoff)
            backoff *= 2
            continue
        except Exception as e:  # pragma: no cover - unexpected environment errors
            return f"Error running scraper: {e!s}"

# @mcp.tool()
# def recall_recipes(keyword: str) -> str:
#     """Search for recipes containing the given keyword and return the ingredients"""
#     ensure_file()
#     results = []
#     with open(RECIPE_FILE, "r") as f:
#         for line in f:
#             if keyword.lower() in line.lower():
#                 results.append(line.strip())
#     return "\n".join(results) if results else "No recipes found."


# # Add a dynamic greeting resource
# @mcp.resource("greeting://{name}")
# def get_greeting(name: str) -> str:
#     """Get a personalized greeting"""
#     return f"Hello, {name}!"


# # Add a prompt
# @mcp.prompt()
# def greet_user(name: str, style: str = "friendly") -> str:
#     """Generate a greeting prompt"""
#     styles = {
#         "friendly": "Please write a warm, friendly greeting",
#         "formal": "Please write a formal, professional greeting",
#         "casual": "Please write a casual, relaxed greeting",
#     }

#     return f"{styles.get(style, styles['friendly'])} for someone named {name}."


# Run with streamable HTTP transport
if __name__ == "__main__":
    mcp.run(transport="streamable-http")