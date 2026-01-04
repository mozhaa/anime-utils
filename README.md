# anime-utils

A Python utility for fetching anime data from multiple sources. Provides async clients for various anime databases, a CLI tool, and MCP server support.

## Features

- **Multiple data sources**: AniDB, IDsMoe, Shikimori, and local AniDB XML files
- **Async clients**: Efficient async/await based clients with rate limiting
- **Caching**: SQLite-based caching to reduce API calls
- **CLI tool**: Command-line interface for quick data access
- **MCP server**: Model Context Protocol server for AI assistant integration

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

```bash
uv install
```

## Usage

### CLI

```bash
# Search anime on Shikimori
anime-utils shikimori search --query "naruto" --limit 5

# Get anime by MAL ID
anime-utils shikimori get-anime --mal-id 1

# Print all available tools
anime-utils print-registry
```

### MCP Server

```bash
# Start MCP server (default: 0.0.0.0:8112)
anime-utils mcp

# Custom host/port
anime-utils mcp --host 127.0.0.1 --port 9000
```

### Python API

```python
import asyncio
from anime_utils import ShikimoriClient

async def main():
    async with ShikimoriClient() as client:
        anime = await client.get_anime(mal_id=1)
        print(anime)

asyncio.run(main())
```

## Clients

| Client | Description |
|--------|-------------|
| `AniDBScraper` | Scrape anime data from AniDB website |
| `IDsMoeClient` | Fetch data from IDsMoe API |
| `ShikimoriClient` | Query Shikimori GraphQL API |
| `LocalClient` | Read local AniDB XML dump file |

## Configuration

Create a configuration file at `anime-utils-config.yaml`. See [example file](anime-utils-config.schema.yaml) for reference.