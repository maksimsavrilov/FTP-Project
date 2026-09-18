import argparse
import unittest

from ftp_project.cli import handlers
from ftp_project.cli.parser import build_parser
from ftp_project.cli.registry import CommandRegistry


class CliRegistryTests(unittest.TestCase):
    def test_parser_attaches_registered_handler_to_leaf_command(self):
        args = build_parser().parse_args(["website", "get", "website-1"])

        self.assertIs(args.handler, handlers.website_get)
        self.assertEqual(args.website_id, "website-1")

    def test_registry_can_register_a_new_command_without_dispatcher_changes(self):
        called = []

        def handler(args, context):
            called.append(args.value)
            return 0

        registry = CommandRegistry()
        registry.register(
            "example", "run", handler=handler,
            arguments=((("value",), {}),),
        )

        parser = argparse.ArgumentParser()
        registry.install(parser)
        args = parser.parse_args(["example", "run", "registered"])

        self.assertEqual(args.handler(args, None), 0)
        self.assertEqual(called, ["registered"])
