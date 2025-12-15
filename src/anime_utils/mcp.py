import argparse
import logging
from typing import Any

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> None:
    import asyncio
    import inspect

    from fastmcp import FastMCP

    from .registry import get_registry

    class ClientManager:
        def __init__(self):
            self._clients = {}

        async def get_client(self, client_cls: type):
            if client_cls not in self._clients:
                self._clients[client_cls] = client_cls()
                await self._clients[client_cls].__aenter__()
            return self._clients[client_cls]

        async def close_all(self):
            for client in self._clients.values():
                await client.__aexit__(None, None, None)
            self._clients.clear()

    client_manager = ClientManager()

    def create_tool_function(client_cls: type, method_name: str, func):
        sig = inspect.signature(func)
        parameters = [p for p in sig.parameters.values() if p.name != "self"]
        param_definition = ", ".join(map(str, parameters))
        param_str = ", ".join(p.name for p in parameters)

        function_code = f"""
from typing import *
async def tool_function({param_definition}) -> Any:
    client = await client_manager.get_client(client_cls)
    method = getattr(client, method_name)
    return await method({param_str})
"""

        local_vars = {
            "client_cls": client_cls,
            "method_name": method_name,
            "Any": Any,
            "client_manager": client_manager,
        }
        exec(function_code, local_vars)
        return local_vars["tool_function"]

    def setup_mcp_tools(mcp: FastMCP) -> None:
        for client in get_registry():
            for tool in client["tools"]:
                tool_name = f"{client['name']}_{tool['name']}"
                method_name = tool["name"]

                func = getattr(client["cls"], tool["name"])
                tool_function = create_tool_function(client["cls"], method_name, func)

                full_description = tool["short_description"]
                if tool["long_description"]:
                    full_description += "\n\n" + tool["long_description"]
                if tool["examples"]:
                    full_description += "\n\nExamples:\n" + tool["examples"]

                mcp.tool(tool_function, name=tool_name, description=full_description)

    mcp = FastMCP("anime-utils")
    setup_mcp_tools(mcp)

    async def async_main() -> None:
        try:
            await mcp.run_async(transport="streamable-http", host=args.host, port=args.port)
        finally:
            await client_manager.close_all()

    asyncio.run(async_main())
