# mcp-futurepedia-crawler

MCP server that exposes Futurepedia crawling logic as tools for assistants.

## What it does

- Fetches a random AI tool from Futurepedia search API
- Opens the tool detail page
- Extracts structured fields (description, what is, key features, pros/cons, who uses, image)
- Returns clean JSON for downstream assistant use

## MCP tools

- `futurepedia_random_tool()` — get one random tool with parsed metadata
- `futurepedia_tools(count=3)` — get several random tools in one call

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m futurepedia_mcp.server
```

The server runs over stdio (default MCP mode).

## Claude Desktop / MCP client config

```json
{
  "mcpServers": {
    "futurepedia": {
      "command": "python",
      "args": ["-m", "futurepedia_mcp.server"],
      "cwd": "/absolute/path/to/mcp-futurepedia-crawler"
    }
  }
}
```

## Environment

Optional:

- `PROXY_URL` — proxy URL used for HTTP requests

## Notes

Crawler logic is adapted from `litvan007/AI-slop-tg` (`src/futurepedia.py`) and wrapped for MCP usage.
