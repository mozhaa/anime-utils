import argparse
import asyncio
import inspect
import logging
from typing import Dict

import docstring_parser

from .sources.anidb.scraper import AniDBScraper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="anime-utils")
    subparsers = parser.add_subparsers()

    clients = [AniDBScraper]

    for client in clients:
        c_parser = subparsers.add_parser(name=client.name, description=inspect.getdoc(client))
        c_subparsers = c_parser.add_subparsers()

        for name, func in inspect.getmembers(AniDBScraper, inspect.isfunction):
            if name.startswith("__"):
                continue

            docstring = inspect.getdoc(func)
            description = ""
            help_texts: Dict[str, str] = {}

            if docstring:
                parsed_doc = docstring_parser.parse(docstring)
                description = parsed_doc.short_description or ""

                for param in parsed_doc.params:
                    help_texts[param.arg_name] = param.description or ""

            t_parser = c_subparsers.add_parser(name=name.replace("_", "-"), description=description)
            for param in inspect.signature(func).parameters.values():
                if param.name == "self":
                    continue

                arg_name = f"--{param.name.replace('_', '-')}"
                help_text = help_texts.get(param.name, "")

                if param.default != inspect.Parameter.empty:
                    t_parser.add_argument(arg_name, type=param.annotation, default=param.default, help=help_text)
                else:
                    t_parser.add_argument(arg_name, type=param.annotation, required=True, help=help_text)

            t_parser.set_defaults(client=client, method_name=name)

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    args = parse_args()

    if not hasattr(args, "client") or not hasattr(args, "method_name"):
        return

    async def run_client():
        client = args.client()
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
            print(result)

    asyncio.run(run_client())


if __name__ == "__main__":
    main()
