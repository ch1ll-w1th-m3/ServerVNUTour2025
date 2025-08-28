"""
Admin-related commands
"""
import discord
from discord.ext import commands


def setup_admin_commands(bot):
    """Setup admin commands"""

    @bot.command(name="ping")
    async def ping(ctx):
        """Kiểm tra độ trễ của bot"""
        latency = round(bot.latency * 1000)
        await ctx.send(f"Pong! Độ trễ: {latency}ms")

    @bot.command(name="info")
    async def info(ctx):
        """Hiển thị thông tin bot"""
        embed = discord.Embed(
            title="VnuTourBot Info",
            description="Bot quản lý tour VNU với các chức năng âm nhạc và quản lý trạm",
            color=0x00ff00,
        )

        embed.add_field(
            name="Thống kê",
            value=f"Servers: {len(bot.guilds)}\nUsers: {len(bot.users)}",
            inline=True,
        )

        embed.add_field(
            name="Độ trễ",
            value=f"{round(bot.latency * 1000)}ms",
            inline=True,
        )

        embed.add_field(
            name="Chức năng",
            value="Âm nhạc YouTube\nQuản lý trạm tour\nLogging tự động",
            inline=False,
        )

        embed.set_footer(text="VnuTourBot v1.0")
        await ctx.send(embed=embed)

    # Public command: assign Discord ID to MSSV
    @bot.command(name="assign")
    async def assign(ctx, mssv: str):
        """Gán Discord ID của bạn vào MSSV trong cơ sở dữ liệu."""
        try:
            mongo = getattr(bot, "mongo", None)
            if not mongo:
                await ctx.send("Hệ thống cơ sở dữ liệu chưa được cấu hình.")
                return

            status, message = mongo.assign_discord_by_mssv(mssv, ctx.author.id)

            # Fetch participant info for confirmation DM
            doc = None
            try:
                doc = mongo.participants.find_one({"mssv": str(mssv).strip()})
            except Exception:
                doc = None

            # Handle different status cases
            if status == "discord_already_used":
                # Send detailed error message to user
                error_embed = discord.Embed(
                    title="❌ **Lỗi: Discord ID đã được sử dụng**",
                    description=message,
                    color=0xe74c3c
                )
                error_embed.add_field(
                    name="🔧 **Cần hỗ trợ**",
                    value="Discord ID của bạn đã được sử dụng bởi MSSV khác. Vui lòng liên hệ admin để được hỗ trợ.",
                    inline=False
                )
                error_embed.add_field(
                    name="📋 **Thông tin MSSV hiện tại**",
                    value=f"MSSV: {mssv}\nHọ và tên: {doc.get('full_name', 'Không có tên') if doc else 'Không tìm thấy'}",
                    inline=False
                )
                
                await ctx.send(embed=error_embed)
                
                # Send notification to Support Ticket channel
                try:
                    support_channel_id = bot.config.support_channel_id
                    if support_channel_id:
                        support_channel = bot.get_channel(support_channel_id)
                        if support_channel:
                            support_embed = discord.Embed(
                                title="🚨 **Yêu cầu hỗ trợ: Discord ID Conflict**",
                                description=f"Người dùng {ctx.author.mention} gặp vấn đề khi liên kết MSSV",
                                color=0xf39c12
                            )
                            support_embed.add_field(
                                name="👤 **Người dùng**",
                                value=f"Discord: {ctx.author.mention} (ID: {ctx.author.id})\nTên: {ctx.author.display_name}",
                                inline=False
                            )
                            support_embed.add_field(
                                name="📋 **MSSV yêu cầu**",
                                value=f"MSSV: {mssv}\nHọ và tên: {doc.get('full_name', 'Không có tên') if doc else 'Không tìm thấy'}",
                                inline=False
                            )
                            support_embed.add_field(
                                name="⚠️ **Vấn đề**",
                                value="Discord ID đã được sử dụng bởi MSSV khác. Cần admin hỗ trợ để giải quyết conflict.",
                                inline=False
                            )
                            support_embed.add_field(
                                name="🕒 **Thời gian**",
                                value=discord.utils.format_dt(discord.utils.utcnow(), style='F'),
                                inline=False
                            )
                            
                            await support_channel.send(embed=support_embed)
                except Exception as e:
                    print(f"[SUPPORT ERROR] Không thể gửi thông báo đến Support channel: {e}")
                
                return

            # Send DM with details (private) for other cases
            try:
                embed = discord.Embed(
                    title="Kết quả liên kết MSSV",
                    description=message,
                    color=0x2ecc71 if status in ("ok", "already_linked") else 0xe67e22,
                )
                if doc:
                    embed.add_field(name="Họ và tên", value=doc.get("full_name") or "-", inline=False)
                    embed.add_field(name="MSSV", value=doc.get("mssv") or "-", inline=True)
                    team = doc.get("team_name") or doc.get("team_id") or "-"
                    embed.add_field(name="Tên đội", value=str(team), inline=True)
                
                # Thêm thông tin chi tiết về trạng thái
                if status == "already_assigned":
                    embed.add_field(
                        name="⚠️ Lưu ý", 
                        value="MSSV này đã được liên kết với tài khoản Discord khác. Nếu bạn nghĩ đây là lỗi, vui lòng liên hệ admin.", 
                        inline=False
                    )
                elif status == "already_linked":
                    embed.add_field(
                        name="ℹ️ Thông tin", 
                        value="MSSV này đã được liên kết với Discord của bạn rồi.", 
                        inline=False
                    )
                
                await ctx.author.send(embed=embed)
                await ctx.reply("Đã gửi thông tin xác nhận qua tin nhắn riêng (DM).", mention_author=False)
            except discord.Forbidden:
                await ctx.send(message + " (Không thể gửi DM, vui lòng mở DM)")

        except Exception as e:
            await ctx.send(f"Lỗi: {e}")

    # Public command: check participant information
    @bot.command(name="check")
    async def check(ctx, mssv: str = None):
        """Kiểm tra thông tin tham gia viên. Nếu không có MSSV, kiểm tra Discord ID của bạn."""
        try:
            mongo = getattr(bot, "mongo", None)
            if not mongo:
                await ctx.send("Hệ thống cơ sở dữ liệu chưa được cấu hình.")
                return

            # If no MSSV provided, check by Discord ID
            if not mssv:
                doc = mongo.participants.find_one({"discord_id": ctx.author.id})
                if not doc:
                    await ctx.send("❌ **Không tìm thấy thông tin:** Bạn chưa liên kết MSSV nào với Discord của mình.\nSử dụng `!assign <mssv>` để liên kết.")
                    return
                mssv = doc.get("mssv")
            else:
                # Check by MSSV
                doc = mongo.participants.find_one({"mssv": str(mssv).strip()})
                if not doc:
                    await ctx.send(f"❌ **Không tìm thấy:** MSSV {mssv} không tồn tại trong hệ thống.")
                    return

            # Create detailed embed
            embed = discord.Embed(
                title="📋 Thông tin tham gia viên",
                color=0x3498db
            )
            
            embed.add_field(name="👤 **Họ và tên**", value=doc.get("full_name") or "-", inline=False)
            embed.add_field(name="🆔 **MSSV**", value=doc.get("mssv") or "-", inline=True)
            embed.add_field(name="📧 **Email**", value=doc.get("email") or "-", inline=True)
            embed.add_field(name="📱 **Số điện thoại**", value=doc.get("phone") or "-", inline=True)
            embed.add_field(name="🏫 **Trường**", value=doc.get("school") or "-", inline=True)
            embed.add_field(name="🎓 **Khoa**", value=doc.get("faculty") or "-", inline=True)
            embed.add_field(name="📘 **Facebook**", value=doc.get("facebook") or "-", inline=True)
            
            # Team information
            team = doc.get("team_name") or doc.get("team_id") or "-"
            embed.add_field(name="👥 **Tên đội**", value=str(team), inline=True)
            
            # Discord link status
            discord_id = doc.get("discord_id")
            if discord_id:
                if int(discord_id) == ctx.author.id:
                    embed.add_field(name="🔗 **Trạng thái Discord**", value="✅ Đã liên kết với bạn", inline=True)
                else:
                    embed.add_field(name="🔗 **Trạng thái Discord**", value=f"⚠️ Liên kết với Discord ID khác: {discord_id}", inline=True)
            else:
                embed.add_field(name="🔗 **Trạng thái Discord**", value="❌ Chưa liên kết", inline=True)
            
            # Timestamp
            if doc.get("updated_at"):
                embed.add_field(name="🕒 **Cập nhật lần cuối**", value=doc.get("updated_at").strftime("%d/%m/%Y %H:%M:%S"), inline=False)

            # Send DM with detailed info
            try:
                await ctx.author.send(embed=embed)
                await ctx.reply("📬 Đã gửi thông tin chi tiết qua tin nhắn riêng (DM).", mention_author=False)
            except discord.Forbidden:
                # If DM fails, send public response (less detailed)
                public_embed = discord.Embed(
                    title=f"📋 Thông tin MSSV {doc.get('mssv')}",
                    description=f"**Họ và tên:** {doc.get('full_name')}\n**Đội:** {team}",
                    color=0x3498db
                )
                await ctx.send(embed=public_embed)
                await ctx.send("💡 **Gợi ý:** Mở DM để nhận thông tin chi tiết hơn.")

        except Exception as e:
            await ctx.send(f"❌ **Lỗi:** {e}")

    @bot.command(name="syncstatus")
    async def syncstatus(ctx):
        """Xem trạng thái đồng bộ Google Sheet -> MongoDB."""
        try:
            mongo = getattr(bot, "mongo", None)
            if not mongo:
                await ctx.send("Hệ thống cơ sở dữ liệu chưa được cấu hình.")
                return

            last_at = mongo.get_meta("sheet_last_sync_at")
            last_result = mongo.get_meta("sheet_last_result") or {"created": 0, "updated": 0}
            hash_short = (mongo.get_meta("sheet_hash") or "")[:10]

            embed = discord.Embed(title="Trạng thái đồng bộ Google Sheet", color=0x3498db)
            embed.add_field(name="Lần gần nhất", value=str(last_at or "Chưa có"), inline=False)
            embed.add_field(name="Kết quả gần nhất", value=f"tạo: {last_result.get('created',0)}, cập nhật: {last_result.get('updated',0)}", inline=False)
            embed.add_field(name="Hash", value=hash_short or "-", inline=True)
            embed.add_field(name="Khoảng lặp", value=f"{bot.config.sheet_sync_interval}s", inline=True)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Lỗi: {e}")


    @bot.command(name="syncnow")
    @commands.has_permissions(manage_messages=True)
    async def syncnow(ctx):
        """Ép đồng bộ Google Sheet -> MongoDB ngay lập tức (admin)."""
        try:
            cog = bot.get_cog('SheetSyncCog')
            if cog is None or not hasattr(cog, '_sync_once'):
                await ctx.send("Chức năng đồng bộ chưa sẵn sàng hoặc chưa được cấu hình.")
                return
            msg = await ctx.reply("Đang đồng bộ...", mention_author=False)
            await cog._sync_once()
            mongo = getattr(bot, "mongo", None)
            last_result = mongo.get_meta("sheet_last_result") or {"created": 0, "updated": 0}
            await msg.edit(content=f"Đã đồng bộ xong: tạo {last_result.get('created',0)}, cập nhật {last_result.get('updated',0)}")
        except Exception as e:
            await ctx.send(f"Lỗi: {e}")
    @bot.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(ctx, amount: int = 5):
        """Xóa tin nhắn (Admin only)"""
        try:
            if amount > 100:
                await ctx.send("Chỉ có thể xóa tối đa 100 tin nhắn")
                return

            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for command message
            await ctx.send(f"Đã xóa {len(deleted) - 1} tin nhắn", delete_after=5)

        except Exception as e:
            await ctx.send(f"Lỗi: {str(e)}")

    @bot.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
        """Kick thành viên (Admin only)"""
        try:
            await member.kick(reason=reason)
            await ctx.send(f"Đã kick {member.mention}\nLý do: {reason}")

        except Exception as e:
            await ctx.send(f"Lỗi: {str(e)}")

    @bot.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
        """Ban thành viên (Admin only)"""
        try:
            await member.ban(reason=reason)
            await ctx.send(f"Đã ban {member.mention}\nLý do: {reason}")

        except Exception as e:
            await ctx.send(f"Lỗi: {str(e)}")

    @bot.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(ctx, user_id: int):
        """Unban thành viên (Admin only)"""
        try:
            user = await bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"Đã unban {user.mention}")

        except Exception as e:
            await ctx.send(f"Lỗi: {str(e)}")

    @clear.error
    async def clear_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Bạn không có quyền sử dụng lệnh này!")

    @kick.error
    async def kick_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Bạn không có quyền sử dụng lệnh này!")

    @ban.error
    async def ban_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Bạn không có quyền sử dụng lệnh này!")

    @unban.error
    async def unban_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Bạn không có quyền sử dụng lệnh này!")
