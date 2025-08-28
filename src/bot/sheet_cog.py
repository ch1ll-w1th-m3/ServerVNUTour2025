"""
Cog chạy đồng bộ Google Sheet -> MongoDB định kỳ
"""
from __future__ import annotations

from discord.ext import commands, tasks
from datetime import datetime, timezone

from ..utils.sheets import fetch_sheet_rows_and_hash


class SheetSyncCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = bool(
            getattr(bot, "mongo", None)
            and bot.config.google_sheet_api_key
            and bot.config.google_sheet_id
        )
        self.interval = bot.config.sheet_sync_interval
        if self.enabled:
            # Bind the loop with dynamic interval
            self.sheet_sync_loop.change_interval(seconds=max(30, self.interval))
            self.sheet_sync_loop.start()

    def cog_unload(self):
        if self.sheet_sync_loop.is_running():
            self.sheet_sync_loop.cancel()

    async def _sync_once(self):
        mongo = getattr(self.bot, "mongo", None)
        if not mongo:
            return
        # Log start
        if getattr(self.bot, "logger", None):
            try:
                print("Đang đồng bộ Google Sheet -> MongoDB...")
            except Exception:
                pass
        rows, h = await fetch_sheet_rows_and_hash(
            self.bot.config.google_sheet_api_key,
            self.bot.config.google_sheet_id,
            self.bot.config.google_sheet_range,
        )
        prev = mongo.get_meta("sheet_hash")
        if prev == h:
            # Update last sync time even if no changes
            mongo.set_meta("sheet_last_sync_at", datetime.now(timezone.utc).isoformat())
            return
        result = mongo.sync_from_rows([r for r in rows if r.get("mssv")])
        mongo.set_meta("sheet_hash", h)
        mongo.set_meta("sheet_last_sync_at", datetime.now(timezone.utc).isoformat())
        mongo.set_meta("sheet_last_result", result)
        # Log result
        if getattr(self.bot, "logger", None):
            try:
                await self.bot.logger.log(f"Đồng bộ xong: tạo {result['created']}, cập nhật {result['updated']}")
            except Exception:
                pass

    @tasks.loop(seconds=60)  # This will be overridden by change_interval in __init__
    async def sheet_sync_loop(self):
        try:
            await self._sync_once()
        except Exception as e:
            print(f"[SHEET SYNC ERROR] {e}")

    @sheet_sync_loop.before_loop
    async def before_sheet_sync(self):
        # Wait for bot ready, then run an immediate sync before entering the interval loop
        await self.bot.wait_until_ready()
        try:
            await self._sync_once()
        except Exception as e:
            print(f"[SHEET SYNC ERROR] {e}")


async def setup_sheet_sync(bot: commands.Bot):
    await bot.add_cog(SheetSyncCog(bot))
