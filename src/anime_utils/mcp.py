import inspect
import logging
from typing import Any

from fastmcp import FastMCP

from .registry import get_registry

logger = logging.getLogger(__name__)

mcp = FastMCP("anime-utils")


def create_tool_function(client_cls: type, method_name: str):
    method = getattr(client_cls, method_name)
    sig = inspect.signature(method)

    params = []
    param_names = []
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        params.append(inspect.Parameter(param_name, param.kind, default=param.default, annotation=param.annotation))
        param_names.append(param_name)

    param_str = ", ".join(param_names)

    function_code = f"""
async def tool_function({param_str}) -> Any:
    client = client_cls()
    method = getattr(client, method_name)

    async with client:
        return await method({param_str})
"""

    local_vars = {"client_cls": client_cls, "method_name": method_name, "Any": Any}
    exec(function_code, local_vars)
    return local_vars["tool_function"]


def setup_mcp_tools() -> None:
    for client in get_registry():
        for tool in client["tools"]:
            tool_name = f"{client['name']}_{tool['name']}"
            method_name = tool["name"]

            tool_function = create_tool_function(client["cls"], method_name)
            mcp.tool(tool_function, name=tool_name, description=tool["description"])


setup_mcp_tools()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
