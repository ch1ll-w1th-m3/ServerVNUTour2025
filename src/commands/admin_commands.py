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
        await ctx.send(f"🏓 **Pong!** Độ trễ: {latency}ms")
    
    @bot.command(name="info")
    async def info(ctx):
        """Hiển thị thông tin bot"""
        embed = discord.Embed(
            title="🤖 VnuTourBot Info",
            description="Bot quản lý tour VNU với các chức năng âm nhạc và quản lý trạm",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📊 **Thống kê**",
            value=f"**Servers:** {len(bot.guilds)}\n**Users:** {len(bot.users)}",
            inline=True
        )
        
        embed.add_field(
            name="⚡ **Độ trễ**",
            value=f"{round(bot.latency * 1000)}ms",
            inline=True
        )
        
        embed.add_field(
            name="🔧 **Chức năng**",
            value="🎵 Phát nhạc YouTube\n🏁 Quản lý trạm tour\n📝 Logging tự động",
            inline=False
        )
        
        embed.set_footer(text="VnuTourBot v1.0")
        await ctx.send(embed=embed)
    
    @bot.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(ctx, amount: int = 5):
        """Xóa tin nhắn (Admin only)"""
        try:
            if amount > 100:
                await ctx.send("❌ Chỉ có thể xóa tối đa 100 tin nhắn")
                return
            
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for command message
            await ctx.send(f"🗑️ **Đã xóa {len(deleted) - 1} tin nhắn**", delete_after=5)
            
        except Exception as e:
            await ctx.send(f"❌ **Lỗi:** {str(e)}")
    
    @bot.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
        """Kick thành viên (Admin only)"""
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 **Đã kick {member.mention}**\n**Lý do:** {reason}")
            
        except Exception as e:
            await ctx.send(f"❌ **Lỗi:** {str(e)}")
    
    @bot.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(ctx, member: discord.Member, *, reason: str = "Không có lý do"):
        """Ban thành viên (Admin only)"""
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 **Đã ban {member.mention}**\n**Lý do:** {reason}")
            
        except Exception as e:
            await ctx.send(f"❌ **Lỗi:** {str(e)}")
    
    @bot.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(ctx, user_id: int):
        """Unban thành viên (Admin only)"""
        try:
            user = await bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"✅ **Đã unban {user.mention}**")
            
        except Exception as e:
            await ctx.send(f"❌ **Lỗi:** {str(e)}")
    
    @clear.error
    async def clear_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bạn không có quyền sử dụng lệnh này!")
    
    @kick.error
    async def kick_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bạn không có quyền sử dụng lệnh này!")
    
    @ban.error
    async def ban_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bạn không có quyền sử dụng lệnh này!")
    
    @unban.error
    async def unban_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bạn không có quyền sử dụng lệnh này!")




