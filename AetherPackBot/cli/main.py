"""AetherPackBot CLI entry module.

This module keeps CLI access under the new `AetherPackBot.cli` namespace
while delegating implementation to the existing core CLI logic.
"""

from core.cli.main import *  # noqa: F403
