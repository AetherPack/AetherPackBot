"""Console-script launcher for `python -m AetherPackBot.cli`."""

from AetherPackBot.cli.main import run_cli


def main() -> int:
    """Run CLI and return process exit code."""
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
