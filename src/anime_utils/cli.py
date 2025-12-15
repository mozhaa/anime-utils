import argparse
import logging
from typing import Dict, Literal, Union, _type_repr, get_args, get_origin

from .mcp import run as run_mcp
from .registry import get_registry


class RawTextArgumentDefaultsHelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="anime-utils")
    parser.add_argument("--no-pretty-print", action="store_true", help="minify JSON in the output")
    subparsers = parser.add_subparsers()

    for client in get_registry():
        c_parser = subparsers.add_parser(name=client["name"], description=client["description"])
        c_subparsers = c_parser.add_subparsers()

        for tool in client["tools"]:
            help_text = tool["long_description"]
            if tool["examples"]:
                help_text += "\n\nExamples:\n" + tool["examples"]

            t_parser = c_subparsers.add_parser(
                name=tool["name"].replace("_", "-"),
                description=tool["short_description"],
                epilog=help_text,
                formatter_class=RawTextArgumentDefaultsHelpFormatter,
            )
            for param in tool["parameters"]:
                param_name = f"--{param['name'].replace('_', '-')}"

                type_ = param["type_"]
                choices = None
                if get_origin(type_) is Literal:
                    choices = list(get_args(type_))
                    type_ = str

                if type_ is bool:
                    if param["default"] is True:
                        raise RuntimeError(
                            "bool arguments with default value False are not supported "
                            f"({client['name']}.{tool['name']}.{param['name']})"
                        )
                    t_parser.add_argument(param_name, action="store_true", help=param["description"])
                elif param["default"] is not None:
                    t_parser.add_argument(
                        param_name,
                        type=type_,
                        default=param["default"],
                        choices=choices,
                        help=param["description"],
                    )
                else:
                    t_parser.add_argument(
                        param_name,
                        type=type_,
                        required=not is_optional(type_),
                        choices=choices,
                        help=param["description"],
                    )

            t_parser.set_defaults(client=client, method_name=tool["name"])

    mcp_parser = subparsers.add_parser(name="mcp", description="anime-utils MCP server")
    mcp_parser.add_argument("--host", type=str, default="0.0.0.0", help="host to bind the MCP server to")
    mcp_parser.add_argument("--port", type=int, default=8112, help="port to bind the MCP server to")
    mcp_parser.set_defaults(command="mcp")

    print_registry_parser = subparsers.add_parser(name="print-registry", description="print available tools")
    print_registry_parser.add_argument("-H", type=int, default=1, help="root header size")
    print_registry_parser.set_defaults(command="print_registry")

    return parser.parse_args()


def is_optional(field: type) -> bool:
    return get_origin(field) is Union and type(None) in get_args(field)


def get_type_name(type_: type) -> str:
    if get_origin(type_) is Literal:
        type_ = get_args(type_)[0]
        if not isinstance(type_, type):
            type_ = type(type_)
    return _type_repr(type_).replace("typing.", "")


def print_registry(args: argparse.Namespace) -> None:
    registry = get_registry()
    header_prefix = (args.H - 1) * "#"

    for client in registry:
        for tool in client["tools"]:
            tool_name = f"{client['name']}_{tool['name']}"
            print(header_prefix + f"# {tool_name}")
            print(f"{tool['short_description']}\n")

            if tool["long_description"]:
                print(f"{tool['long_description']}\n")

            if tool["parameters"]:
                print(header_prefix + "## Parameters:")
                for param in tool["parameters"]:
                    param_type = get_type_name(param["type_"])

                    default = f" (default: {param['default']})" if param["default"] is not None else ""

                    if param["default"] is None and not is_optional(param["type_"]):
                        required = " (required)"
                    else:
                        required = ""

                    description = param["description"]
                    if "\n" in description:
                        lines = description.split("\n")
                        description = lines[0] + "\n" + "\n".join("  " + line for line in lines[1:])

                    print(f"- `{param['name']}` [{param_type}]: {description} {default}{required}")
                print()

            if tool["examples"]:
                print(header_prefix + "## Examples:")
                print(tool["examples"])
                print()

            print("---\n")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s", datefmt="%H:%M:%S"
    )
    args = parse_args()

    if hasattr(args, "command"):
        if args.command == "mcp":
            run_mcp(args)
        elif args.command == "print_registry":
            print_registry(args)
        return

    if not hasattr(args, "client") or not hasattr(args, "method_name"):
        return

    import asyncio
    import inspect
    import json

    async def run():
        client = args.client["cls"]()
        method_name = args.method_name
        method = getattr(client, method_name)
        method_args: Dict[str, str] = {}
        for param_name in inspect.signature(method).parameters.keys():
            if param_name == "self":
                continue

            cli_arg_name = param_name.replace("-", "_")
            if hasattr(args, cli_arg_name):
                method_args[param_name] = getattr(args, cli_arg_name)

        async with client:
            result = await method(**method_args)
            if args.no_pretty_print:
                output = json.dumps(result)
            else:
                output = json.dumps(result, indent=2)
            print(output)

    asyncio.run(run())


if __name__ == "__main__":
    main()
