"""Lazy command dispatch for GestureVision workflows."""

import argparse
from importlib import import_module
from pathlib import Path

from .config import load_config

COMMANDS = ("capture", "train", "infer", "gamepad")


def _add_config_options(parser):
    parser.add_argument("--config", type=Path, default=argparse.SUPPRESS, help="YAML configuration overlay")
    parser.add_argument("--root", type=Path, default=argparse.SUPPRESS, help="project root for relative paths")
    parser.add_argument("--camera-index", type=int, default=argparse.SUPPRESS, help="camera index override")


def build_parser():
    parser = argparse.ArgumentParser(prog="gesture-vision")
    _add_config_options(parser)
    subparsers = parser.add_subparsers(dest="command", title="commands")
    for command in COMMANDS:
        subparser = subparsers.add_parser(command, help=f"run the {command} workflow")
        _add_config_options(subparser)
    return parser


def load_command_config(args):
    overrides = {"CAMERA": {"camera_index": args.camera_index}} if hasattr(args, "camera_index") else None
    return load_config(getattr(args, "config", None), overrides, getattr(args, "root", None))


def _dispatch(command, config):
    module_name = f"gesture_vision.workflows.{command}"
    try:
        workflow = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name in ("gesture_vision.workflows", module_name):
            raise SystemExit(f"The {command} workflow is not available in this work unit.") from error
        raise
    return workflow.run(config)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return _dispatch(args.command, load_command_config(args))


if __name__ == "__main__":
    main()
