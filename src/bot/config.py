"""
Bot configuration management
"""
import os
from pathlib import Path
from dotenv import load_dotenv


class BotConfig:
    """Bot configuration class"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv(Path(__file__).parent.parent.parent / ".env")
        
        # Bot token
        self.token = os.getenv("DISCORD_TOKEN")
        if not self.token:
            raise RuntimeError("Thiếu DISCORD_TOKEN trong .env")
        
        # Channel IDs
        self.welcome_channel_id = self._safe_int(os.getenv("WELCOME_CHANNEL_ID"))
        self.log_channel_id = self._safe_int(os.getenv("LOG_CHANNEL_ID"))
        self.support_channel_id = self._safe_int(os.getenv("SUPPORT_ROLE"))
        self.team_category_id = self._safe_int(os.getenv("CATEGORYIDFORTEAM"))
        
        # FFmpeg configuration
        self.ffmpeg_exe = os.getenv("FFMPEG_EXE") or "ffmpeg"
        
        # Bot prefix
        self.prefix = "!"

        # Intents
        self.intents = {
            "message_content": True,
            "members": True,
            "guilds": True,
            "voice_states": True
        }

        # MongoDB configuration (optional but recommended)
        # MongoDB connection string is stored under key `MongoDB` in .env
        self.mongodb_uri = os.getenv("MongoDB")
        self.mongodb_db = os.getenv("MONGODB_DB_NAME", "vnutour")

        # Google Sheets sync configuration
        self.google_sheet_api_key = os.getenv("GoogleSheetAPI")
        self.google_sheet_id = os.getenv("GoogleSheetID")
        self.google_sheet_range = os.getenv("GOOGLE_SHEET_RANGE", "A1:K")
        # sync interval: default 60s, minimum 30s
        try:
            interval = int(os.getenv("SHEET_SYNC_INTERVAL", "60"))
        except ValueError:
            interval = 60
        self.sheet_sync_interval = max(30, interval)
    
    def _safe_int(self, value: str) -> int:
        """Safely convert string to int"""
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None
    
    def get_intents(self):
        """Get Discord intents configuration"""
        import discord
        intents = discord.Intents.default()
        for key, value in self.intents.items():
            setattr(intents, key, value)
        return intents




