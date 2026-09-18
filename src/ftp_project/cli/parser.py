"""Argument parser assembled from the central command registry."""

import argparse

from .commands import register_all
from .registry import CommandRegistry


def build_registry() -> CommandRegistry:
    registry = CommandRegistry()
    register_all(registry)
    return registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ftp-project")
    build_registry().install(parser)
    return parser
