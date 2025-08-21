"""
Help command for bot
"""
import discord
from discord.ext import commands


def setup_help_command(bot):
    """Setup help command"""
    
    @bot.command(name="help", aliases=["h", "commands"])
    async def help_command(ctx, command_name: str = None):
        """Hiển thị hướng dẫn sử dụng"""
        
        if command_name:
            # Show help for specific command
            command = bot.get_command(command_name)
            if not command:
                await ctx.send(f"❌ Không tìm thấy lệnh `{command_name}`")
                return
            
            embed = discord.Embed(
                title=f"📖 Lệnh: {command.name}",
                description=command.help or "Không có mô tả",
                color=0x00ff00
            )
            
            if command.aliases:
                embed.add_field(
                    name="🔄 **Tên viết tắt**",
                    value=", ".join(command.aliases),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return
        
        # Show general help
        embed = discord.Embed(
            title="🤖 **VnuTourBot - Hướng dẫn sử dụng**",
            description="Bot quản lý tour VNU với các chức năng âm nhạc và quản lý trạm",
            color=0x00ff00
        )
        
        # Music commands
        embed.add_field(
            name="🎵 **Lệnh âm nhạc**",
            value=(
                "`!play <tên/URL>` - Phát nhạc\n"
                "`!skip` - Bỏ qua bài hát hiện tại\n"
                "`!queue` - Hiển thị queue nhạc\n"
                "`!stop` - Dừng phát nhạc\n"
                "`!volume <0-200>` - Điều chỉnh âm lượng (phần trăm, áp dụng ngay lập tức)\n"
                "`!exit` - Thoát khỏi voice channel"
            ),
            inline=False
        )
        
        # Tour commands
        embed.add_field(
            name="🏁 **Lệnh tour**",
            value=(
                "`!stations` - Danh sách trạm\n"
                "`!checkin <id> <tên đội>` - Check-in\n"
                "`!checkout <tên đội>` - Check-out\n"
                "`!mystation` - Trạm hiện tại\n"
                "`!leaderboard` - Bảng xếp hạng"
            ),
            inline=False
        )
        
        # Admin commands
        embed.add_field(
            name="🔧 **Lệnh admin**",
            value=(
                "`!ping` - Kiểm tra độ trễ\n"
                "`!info` - Thông tin bot\n"
                "`!clear <số>` - Xóa tin nhắn\n"
                "`!kick <@user> <lý do>` - Kick\n"
                "`!ban <@user> <lý do>` - Ban"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 **Ghi chú**",
            value="Sử dụng `!help <tên lệnh>` để xem chi tiết lệnh cụ thể",
            inline=False
        )
        
        embed.set_footer(text="Prefix: ! | VnuTourBot v1.0")
        await ctx.send(embed=embed)
