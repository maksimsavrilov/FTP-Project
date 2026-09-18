"""Central command registry backed by argparse subparsers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any, Callable


Handler = Callable[[argparse.Namespace, Any], int]


@dataclass(frozen=True)
class CommandSpec:
    path: tuple[str, ...]
    handler: Handler
    arguments: tuple[tuple[tuple[str, ...], dict[str, Any]], ...] = ()


@dataclass
class CommandRegistry:
    """Declarative map from command paths to handler functions."""

    specs: list[CommandSpec] = field(default_factory=list)

    def register(
        self,
        *path: str,
        handler: Handler,
        arguments: tuple[tuple[tuple[str, ...], dict[str, Any]], ...] = (),
    ) -> None:
        self.specs.append(CommandSpec(tuple(path), handler, arguments))

    def install(self, parser: argparse.ArgumentParser) -> None:
        prefixes = {
            spec.path[:index]
            for spec in self.specs
            for index in range(1, len(spec.path))
        }
        subparsers: dict[tuple[str, ...], Any] = {
            (): parser.add_subparsers(dest="command", required=True)
        }
        parsers: dict[tuple[str, ...], argparse.ArgumentParser] = {(): parser}

        for spec in self.specs:
            for depth, name in enumerate(spec.path):
                parent_path = spec.path[:depth]
                current_path = spec.path[: depth + 1]
                if current_path not in parsers:
                    command_parser = subparsers[parent_path].add_parser(name)
                    parsers[current_path] = command_parser
                    if current_path in prefixes:
                        subparsers[current_path] = command_parser.add_subparsers(
                            dest=f"{name.replace('-', '_')}_command", required=True
                        )
            command_parser = parsers[spec.path]
            command_parser.set_defaults(handler=spec.handler)
            for flags, kwargs in spec.arguments:
                command_parser.add_argument(*flags, **kwargs)
