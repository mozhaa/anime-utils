import inspect
from typing import Any, TypedDict

import docstring_parser

from .sources.anidb.scraper import AniDBScraper
from .sources.base import BaseClient


class Parameter(TypedDict):
    name: str
    description: str
    type_: type
    default: Any


class Tool(TypedDict):
    name: str
    method_name: str
    description: str
    parameters: list[Parameter]


class Client(TypedDict):
    cls: type[BaseClient]
    name: str
    description: str
    tools: list[Tool]


clients = [AniDBScraper]


def get_registry() -> list[Client]:
    registry = []
    for client in clients:
        tools = []
        for name, func in inspect.getmembers(client, inspect.isfunction):
            if name.startswith("__"):
                continue

            docstring = inspect.getdoc(func)
            if docstring is None:
                raise RuntimeError(f"{client.name}.{name} does not have a docstring")
            parsed_doc = docstring_parser.parse(docstring)

            help_texts: dict[str, str] = {}
            for param in parsed_doc.params:
                help_texts[param.arg_name] = param.description

            params = []
            for param in inspect.signature(func).parameters.values():
                if param.name == "self":
                    continue

                params.append(
                    Parameter(
                        name=f"--{param.name.replace('_', '-')}",
                        description=help_texts.get(param.name, ""),
                        type_=param.annotation,
                        default=param.default if not inspect.Parameter.empty else None,
                    )
                )

            tools.append(
                Tool(
                    name=name.replace("_", "-"),
                    method_name=name,
                    description=parsed_doc.short_description,
                    parameters=params,
                )
            )
        registry.append(
            Client(
                cls=client,
                name=client.name,
                description=inspect.getdoc(client),
                tools=tools,
            )
        )
    return registry
