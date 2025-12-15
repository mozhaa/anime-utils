import argparse
import asyncio
import inspect
import json
import logging
from typing import Dict, Literal, get_args, get_origin

from .registry import get_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="anime-utils")
    subparsers = parser.add_subparsers()

    for client in get_registry():
        c_parser = subparsers.add_parser(name=client["name"], description=client["description"])
        c_subparsers = c_parser.add_subparsers()

        for tool in client["tools"]:
            t_parser = c_subparsers.add_parser(name=tool["name"].replace("_", "-"), description=tool["description"])
            for param in tool["parameters"]:
                param_name = f"--{param['name'].replace('_', '-')}"

                type_ = param["type_"]
                choices = None
                if get_origin(type_) is Literal:
                    choices = list(get_args(type_))
                    type_ = str

                if param["default"] is not None:
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
                        required=True,
                        choices=choices,
                        help=param["description"],
                    )

            t_parser.set_defaults(client=client, method_name=tool["name"])

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s", datefmt="%H:%M:%S"
    )
    args = parse_args()

    if not hasattr(args, "client") or not hasattr(args, "method_name"):
        return

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
            print(json.dumps(result))

    asyncio.run(run())


if __name__ == "__main__":
    main()
