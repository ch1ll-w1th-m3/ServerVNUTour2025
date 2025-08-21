"""
Member-related events (join, leave, etc.)
"""
import discord


def setup_member_events(bot):
    """Setup member event handlers"""
    
    @bot.event
    async def on_member_join(member: discord.Member):
        """Called when a member joins the guild"""
        await bot.logger.log_member_join(member)
        
        # Welcome message
        if bot.config.welcome_channel_id:
            try:
                welcome_channel = bot.get_channel(bot.config.welcome_channel_id)
                if welcome_channel:
                    welcome_msg = (
                        f"🎉 **Chào mừng {member.mention} đến với server!**\n"
                        f"Bạn là thành viên thứ {member.guild.member_count} của server.\n"
                        f"Chúc bạn có những trải nghiệm tuyệt vời! 🚀"
                    )
                    await welcome_channel.send(welcome_msg)
            except Exception as e:
                print(f"[WELCOME ERROR] {e}")
    
    @bot.event
    async def on_member_remove(member: discord.Member):
        """Called when a member leaves the guild"""
        await bot.logger.log_member_leave(member)
    
    @bot.event
    async def on_member_update(before: discord.Member, after: discord.Member):
        """Called when a member is updated (nickname, roles, etc.)"""
        # Log role changes
        if before.roles != after.roles:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            if added_roles:
                role_names = ", ".join([role.name for role in added_roles if role.name != "@everyone"])
                if role_names:
                    await bot.logger.log(f"🎭 **{after.mention} được thêm role:** {role_names}")
            
            if removed_roles:
                role_names = ", ".join([role.name for role in removed_roles if role.name != "@everyone"])
                if role_names:
                    await bot.logger.log(f"🎭 **{after.mention} bị mất role:** {role_names}")
        
        # Log nickname changes
        if before.nick != after.nick:
            old_nick = before.nick or before.name
            new_nick = after.nick or after.name
            await bot.logger.log(f"📝 **{after.mention} đổi nickname:** `{old_nick}` → `{new_nick}`")

