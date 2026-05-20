# Darkmine Raw Data MCP

`darkmine-data-mcp` is a minimal read-only MCP server for calling the Darkmine raw GSWA data API (coming soon). 

Darkmine Data MCP  
Copyright (c) 2026 Darkmine Pty Ltd  
Licensed under Apache-2.0

## Installation

Run from a published package:

```bash
uvx darkmine-data-mcp
```

Run locally from this repository:

```bash
uv sync --extra dev
uv run python -m darkmine_data_mcp
```

## API Key Setup

Set the API key in the process environment. Do not pass API keys as tool arguments.

```bash
export DARKMINE_DATA_API_KEY=dm_xxx
export DARKMINE_DATA_BASE_URL=coming_soon
```

Optional settings:

```bash
export DARKMINE_DATA_TIMEOUT_SECONDS=30
export DARKMINE_DATA_MAX_RECORDS=1000
```

## Adding the MCP Server

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "darkmine": {
      "command": "uvx",
      "args": ["darkmine-data-mcp"],
      "env": {
        "DARKMINE_DATA_API_KEY": "dm_xxx",
        "DARKMINE_DATA_BASE_URL": "https://coming-soon"
      }
    }
  }
}
```

Restart Claude Desktop.

### Claude Code

This repo ships a project-scoped `.mcp.json`. From inside a clone of this repo, export your key and start Claude Code:

```bash
export DARKMINE_DATA_API_KEY=dm_xxx
export DARKMINE_DATA_BASE_URL=https://coming-soon
claude
```

Claude Code will prompt to approve the project MCP server on first run.

To register it globally (works in any directory) using the published package:

```bash
claude mcp add darkmine -s user \
  -e DARKMINE_DATA_API_KEY=dm_xxx \
  -e DARKMINE_DATA_BASE_URL=https://coming-soon \
  -- uvx darkmine-data-mcp
```

Verify with `claude mcp list`.

### claude.ai

claude.ai connectors require a remote HTTPS MCP endpoint. This server is a local stdio server and cannot be added to claude.ai directly. A hosted remote variant is coming in future — see the Darkmine docs.

## Tools

GSWA data access tools are prefixed with `gswa_` so future MCP tools can add other data collections without ambiguity. The `data_license` tool returns licence and attribution metadata for the data exposed by this server.

- `data_license`: return licence, attribution, source, and modification-notice requirements for Darkmine-served data.
- `gswa_list_tables`: list raw GSWA tables and supported query methods.
- `gswa_describe_table`: return schema, columns, relationships, and supported filters for one table.
- `gswa_query_table`: bounded generic access to `GET /v1/raw/gswa/tables/{table_name}/rows`.
- `gswa_find_drillholes`: query `dbo_collar` drillhole collar/location records.
- `gswa_get_drillhole_family`: query `/v1/raw/gswa/collar-family` for rows related to matching drillholes.
- `gswa_query_drillhole_geochemistry_raw`: query `dbo_dhgeochemistry` and `dbo_dhgeochemistryattr` together.
- `gswa_query_drillhole_geochemistry_flat`: query flattened drillhole assay rows from `gsd_dhassayflat`.
- `gswa_query_drillhole_geochemistry_summary`: query flattened per-hole assay summaries from `gsd_dhassayflatsummary`.
- `gswa_find_surface_samples`: query `dbo_surfacesample` sample/location records.
- `gswa_get_surface_sample_family`: query `/v1/raw/gswa/surface-sample-family` for rows related to matching surface samples.
- `gswa_query_surface_geochemistry_raw`: query `dbo_surfacesample` and `dbo_surfacesampleattr` together.
- `gswa_query_surface_geochemistry_flat`: query flattened surface assay rows from `gsd_ssassayflat`.

## Raw vs Flat Geochemistry

GSWA drillhole and surface sample geochemistry are exposed in two useful forms:

- Raw EAV tables preserve the source parent rows plus key/value attribute rows.
- Flattened assay tables pivot analytes into columns and are easier for quick summaries.

These forms are not equivalent in the raw source data. Use raw EAV tools for source fidelity and traceability. Use flat tools for convenient analysis. When precision matters, compare both.

## Example Prompts

```text
Using Darkmine, list the GSWA tables and show me which ones support bbox queries.
```

```text
Using Darkmine, find GSWA drillholes in bbox [115.0, -32.0, 116.0, -31.0].
```

```text
Using Darkmine, get both raw EAV and flattened GSWA surface geochemistry for bbox [115.0, -32.0, 116.0, -31.0].
```

## Billing Note

Requests go through the Zuplo API gateway and may be billable under your Darkmine API plan. Details will be available when the API goes live.

## Security Note

The server is read-only and only accepts constrained parameters. It does not accept arbitrary URLs, SQL, shell commands, local paths, or API keys as tool inputs. `DARKMINE_DATA_API_KEY` is read only from environment variables and is never returned in tool output.

## Development

```bash
uv sync --extra dev
uv run pytest
```
