# RECIPE RECALL

This was the result of a one-hour AI hackathon organised by [Steel-AI](https://alex-kelly.blog/Sheffield_event_info/event_2_advert_agents.html) (not including the 3 hours of debugging and documentation afterwards!).

Don't you just hate the time it takes to write a food shopping list _every_ week to make the recipes you want to make? Use this project if you want hallucination-free ingredients lists from a reliable source called directly from your preferred LLM. Also refer to this for inspiration for your own agentic AI tools configured using a locally hosted MCP server.

## PROJECT OBJECTIVE

Create a web scraper to extract ingredients from BBC Good Food recipes using the class selector "ingredients-list list", and expose it as an MCP (Model Context Protocol) tool callable from the Continue extension in VS Code. In theory you should be able to use the MCP configuration YAML in Claude Code (untested). For others, you may need a different YAML config file.

## IMPLEMENTATION SUMMARY

1. bbcgoodfood_scraper.py
   - Standalone Python script that searches BBC Good Food recipes
   - Extracts ingredients from ul.ingredients-list.list elements
   - Parses ingredients into quantity/unit/ingredient_name components
   - Handles text formatting quirks (e.g., "50gdried" → "50g dried")
   - Fully functional when run directly

2. fastmcp_quickstart.py
   - MCP server exposing scraper and utilities as callable tools
   - Tools: add_note, add, test_network, search_recipes
   - Uses stdio transport for subprocess communication
   - File logging to recipe_recall.log with timestamps (on the `attempt_refactor` branch)

## ISSUES ENCOUNTERED & SOLUTIONS

Issue 1: Transport-level timeouts (-32001 Request timed out)
  * Problem: HTTP-based transport layer had short default timeouts
  * Solution: Switched from streamable-http to stdio (direct stdin/stdout)
  * Result: ✅ Eliminated transport overhead
  
Note, this wan't the real issue (see other issues below, including the CRITICAL one). HTTP transport likely to be just fine.

Issue 2: ModuleNotFoundError (requests, beautifulsoup4)
  * Problem: Subprocess environment lacked project dependencies
  * Solution: Wrapped scraper invocation with `uv run --with requests,bs4`
  * Result: ✅ Dependencies available to subprocess

Issue 3: YAML syntax error in MCP configuration
  * Problem: Invalid YAML mapping syntax in environment variables
  * Solution: Converted `env: {C:\Windows}` to proper YAML `env: PATH: "C:\\Windows"`
  * Result: ✅ Config file valid and loads correctly

Issue 4: Subprocess command timeout
  * Problem: Increased subprocess timeout from 30s → 120s, MCP timeout 90s → 180s
  * Solution: Acknowledged uv overhead and set reasonable limits
  * Result: ✅ Timeout buffer in place

Issue 5: Subprocess hanging indefinitely (CRITICAL)
  * Problem: subprocess.run() call never returned; logs stopped at subprocess entry
  * Diagnosis: uv run was waiting for stdin input in non-TTY subprocess context
  * Attempted Fix 1: Added --no-progress flag to suppress interactive output
    * Result: ❌ Did not resolve hang
  * Attempted Fix 2: Added excessive logging before/after subprocess call
    * Result: ❌ Did not fix; logs confirmed subprocess never returned
  * Final Solution: Added stdin=subprocess.DEVNULL to explicitly close stdin
    * Result: ✅ RESOLVED - subprocess now completes successfully

## FINAL STATUS

✅ Web scraper fully functional and tested locally

✅ MCP server running without errors

✅ search_recipes tool now executes and returns results

✅ All tools accessible from Continue IDE via MCP interface

✅ Logging infrastructure working and writing to recipe_recall.log


## TECHNICAL STACK

- Language: Python 3.11+
- Dependencies: requests, beautifulsoup4, mcp[cli], pandas
- Package Manager: uv
- MCP Framework: FastMCP
- Transport: stdio
- Target Website: www.bbcgoodfood.com

## KEY LEARNING

1. subprocess.run() in non-TTY environments needs explicit stdin handling
2. uv run requires stdin=subprocess.DEVNULL when called from subprocess without terminal
3. Stdio transport superior to HTTP for MCP server communication
4. File-based logging critical for debugging subprocess execution issues
5. Each dependency isolation layer (uv, subprocess, async) adds complexity; 
   explicit configuration needed at each level

## NEXT STEPS / POTENTIAL IMPROVEMENTS

- Add retry logic for network failures
- Cache search results to reduce BBC Good Food requests
- Extend scraper to extract other recipe metadata (prep time, servings, etc.)
- Add unit tests for ingredient parsing edge cases
- Consider async HTTP client (aiohttp) for parallel recipe fetching

