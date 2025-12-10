"""
FastMCP quickstart example.

Run from the repository root:
    uv run examples/snippets/servers/fastmcp_quickstart.py
"""

from mcp.server.fastmcp import FastMCP
import os
import subprocess
import time
import asyncio
import sys
from typing import Optional
import logging

# Create an MCP server
mcp = FastMCP("Recipe Recall", json_response=False)

# Configure module logger
logger = logging.getLogger("recipe_recall.fastmcp")
if not logger.handlers:
    # Basic configuration for standalone runs; MCP may configure logging itself.
    logging.basicConfig(level=logging.INFO)


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
async def search_recipes(keyword: str) -> dict:
    """Find the ingredients for a given meal search term.

    This tool runs the local `bbcgoodfood_scraper_yolo.py` script using the same
    Python interpreter as the current process. It runs the subprocess in a
    thread (via `asyncio.to_thread`) to avoid blocking the MCP event loop.
    Detailed logging is emitted to help diagnose timeouts and failures.
    """
    script_name = "bbcgoodfood_scraper_yolo.py"
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        # fallback to CWD (useful when server cwd differs)
        script_path = script_name

    cmd = [sys.executable, script_path, keyword]
    logger.info("search_recipes starting; script=%s keyword=%s", script_path, keyword)
    logger.debug("command: %s", cmd)

    start = time.time()
    try:
        # Run subprocess.run inside a thread to keep the async loop responsive.
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=6000,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start
        logger.warning("search_recipes timed out after %.1fs: %s", elapsed, e)
        return {"error": f"scraper timed out after {6000}s"}
    except Exception as e:  # unexpected execution error
        elapsed = time.time() - start
        logger.exception("search_recipes failed after %.1fs: %s", elapsed, e)
        return {"error": f"failed to run scraper: {e!s}"}

    elapsed = time.time() - start
    logger.info("search_recipes finished in %.2fs with returncode=%s", elapsed, result.returncode)
    # log sizes rather than full output at INFO to avoid noisy logs; DEBUG will include full output
    logger.info("stdout length=%d stderr length=%d", len(result.stdout or ""), len(result.stderr or ""))
    logger.debug("scraper stdout:\n%s", result.stdout)
    logger.debug("scraper stderr:\n%s", result.stderr)

    if result.returncode != 0:
        return {"error": result.stderr or f"scraper exited {result.returncode}"}
    return {"output": result.stdout or ""}

# @mcp.tool()
# async def search_recipes(keyword: str, timeout: int = 10) -> str:
#     """Find the ingredients for a given meal search term
#     Args:
#         keyword (str): The name of a single recipe to search.
#     Returns:
#         str: The ingredients from the recipe.
#     """
#     # Attempt to run the local scraper script and return its stdout.
#     # Use subprocess.run with a timeout, retries and clear error handling so
#     # the MCP tool doesn't fail silently or return an integer exit code.
#     script_name = "bbcgoodfood_scraper_yolo.py"
#     script_path = os.path.join(os.path.dirname(__file__), script_name)
#     if not os.path.exists(script_path):
#         script_path = script_name

#     max_retries = 4
#     timeout_seconds = 60
#     backoff = 2.0

#     for attempt in range(1, max_retries + 1):
#         try:
#             # use the same Python executable and non-blocking subprocess
#             proc = await asyncio.create_subprocess_exec(
#                 sys.executable, script_path, keyword,
#                 stdout=asyncio.subprocess.PIPE,
#                 stderr=asyncio.subprocess.PIPE
#             )
#             try:
#                 stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
#             except asyncio.TimeoutError:
#                 proc.kill()
#                 await proc.wait()
#                 raise asyncio.TimeoutError()
#             output = (stdout.decode("utf-8") or "").strip()
#             ensure_file()
#             # small sync write offloaded to a thread to avoid blocking
#             await asyncio.to_thread(lambda: open(RECIPE_FILE, "a", encoding="utf-8").write(output + "\n"))
#             return output or "(no output)"
#         except asyncio.TimeoutError:
#             if attempt >= max_retries:
#                 return f"Error: scraper timed out after {timeout_seconds}s (attempt {attempt})"
#             await asyncio.sleep(backoff)
#             backoff *= 2
#             continue
#         except Exception as e:
#             return f"Error running scraper: {e!s}"

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