"""
GPS Traffic Control System - Command Line Interface

Main entry point for all CLI operations including running tests,
starting simulations, and managing the system.
"""

import sys
import subprocess
from typing import List, Optional
import argparse

from ..utils.config import Config, ConfigOption, ConfigGlobals
from ..core.sumo import Sumo
from datetime import datetime


def run_tests(args: Optional[List[str]] = None) -> int:
    """Run the test suite using pytest."""
    cmd = ["pytest"]

    if args:
        cmd.extend(args)
    else:
        cmd.extend(["-v", "--cov=src"])

    try:
        result = subprocess.run(cmd, cwd=".")
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Make sure you've installed dev dependencies:")
        print("pip3 install -e .[dev]")
        return 1


def run_simulation(args: List[str]) -> int:
    """Run traffic simulation (placeholder for future implementation)."""
    opts = ConfigOption(
        global_config_overides=ConfigGlobals(timestamp=str(datetime.now()))
    )
    sumo = Sumo({}, Config(opts))
    sumo.connect()
    sumo.run_simulation()

    return 1


def run_train(args: List[str]) -> int:
    """Train RL models (placeholder for future implementation)."""
    print("Model training not yet implemented.")
    print("Args:", args)
    return 0


def run_analyze(args: List[str]) -> int:
    """Analyze traffic data (placeholder for future implementation)."""
    print("Data analysis not yet implemented.")
    print("Args:", args)
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description="GPS Traffic Control System CLI", prog="gps-traffic"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Test command
    test_parser = subparsers.add_parser(
        "test", help="Run the test suite", aliases=["--test"]
    )
    test_parser.add_argument(
        "test_args", nargs="*", help="Additional arguments to pass to pytest"
    )

    # Simulation command
    sim_parser = subparsers.add_parser(
        "simulate", help="Run traffic simulation", aliases=["sim"]
    )
    sim_parser.add_argument("--config", help="Configuration file path")
    sim_parser.add_argument(
        "--duration", type=int, default=3600, help="Simulation duration in seconds"
    )

    # Training command
    train_parser = subparsers.add_parser("train", help="Train RL models")
    train_parser.add_argument(
        "--episodes", type=int, default=1000, help="Number of training episodes"
    )
    train_parser.add_argument(
        "--model-type",
        choices=["dqn", "ppo", "a3c"],
        default="dqn",
        help="RL algorithm to use",
    )

    # Analysis command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze traffic data")
    analyze_parser.add_argument(
        "--data-path", required=True, help="Path to traffic data"
    )
    analyze_parser.add_argument("--output", help="Output file for analysis results")

    return parser


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()

    # Handle special case for --test flag
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        return run_tests(sys.argv[2:])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate command handler
    if args.command in ["test", "--test"]:
        return run_tests(getattr(args, "test_args", None))
    elif args.command in ["simulate", "sim"]:
        return run_simulation(sys.argv[2:])
    elif args.command == "train":
        return run_train(sys.argv[2:])
    elif args.command == "analyze":
        return run_analyze(sys.argv[2:])
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
