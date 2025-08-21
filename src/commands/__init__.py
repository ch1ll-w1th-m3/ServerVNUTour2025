"""
Commands module for bot commands
"""

from .music_commands import setup_music_commands
from .admin_commands import setup_admin_commands
from .tour_commands import setup_tour_commands
from .help_command import setup_help_command


def setup_commands(bot):
    """Setup all bot commands"""
    setup_help_command(bot)  # Setup help command first
    setup_music_commands(bot)
    setup_admin_commands(bot)
    setup_tour_commands(bot)


__all__ = ['setup_commands', 'setup_music_commands', 'setup_admin_commands', 'setup_tour_commands', 'setup_help_command']
