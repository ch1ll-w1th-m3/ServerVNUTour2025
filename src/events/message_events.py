"""
Message event handlers
"""
import discord
from discord.ext import commands
from datetime import datetime, timezone
import re


def setup_message_events(bot):
    """Setup message event handlers"""
    
    @bot.event
    async def on_message(message: discord.Message):
        """Called when a message is sent"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Log message if it's in a monitored channel
        if message.guild and bot.config.log_channel_id:
            # You can add specific channel monitoring logic here
            pass
        
        # Process commands (required for commands to work)
        await bot.process_commands(message)
    
    @bot.event
    async def on_message_edit(before: discord.Message, after: discord.Message):
        """Called when a message is edited"""
        # Ignore bot messages
        if before.author.bot:
            return
        
        # Ignore if content didn't change (e.g., embed updates)
        if before.content == after.content:
            return
        
        await bot.logger.log_message_edit(before, after)
    
    @bot.event
    async def on_message_delete(message: discord.Message):
        """Called when a message is deleted"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        await bot.logger.log_message_delete(message)
    
    @bot.event
    async def on_bulk_message_delete(messages: list[discord.Message]):
        """Called when multiple messages are deleted at once"""
        if not messages:
            return
        
        # Log bulk deletion
        guild = messages[0].guild
        channel = messages[0].channel
        count = len(messages)
        
        log_msg = (
            f"🗑️ **Xóa hàng loạt tin nhắn**\n"
            f"**Kênh:** {channel.mention}\n"
            f"**Số lượng:** {count} tin nhắn\n"
            f"**Thời gian:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')}"
        )
        
        await bot.logger.log(log_msg)
