"""
Slash commands for the bot
"""
import discord
from discord import app_commands
from discord.ext import commands
from ..music.player import get_player, ensure_voice, after_play_callback, force_cleanup_ffmpeg_source
from ..music.ytdlp_handler import ytdlp_extract, build_ffmpeg_options
import asyncio
import threading


class VolumeControlledAudioSource(discord.FFmpegPCMAudio):
    """Custom audio source with volume control"""
    
    def __init__(self, source, volume=1.0, **kwargs):
        super().__init__(source, **kwargs)
        self._volume = volume
    
    @property
    def volume(self):
        return self._volume
    
    @volume.setter
    def volume(self, value):
        self._volume = max(0.0, min(2.0, value))
    
    def read(self):
        """Read audio data with volume applied"""
        data = super().read()
        if data and self._volume != 1.0:
            # Apply volume by scaling the audio data
            import array
            audio_array = array.array('h', data)
            for i in range(len(audio_array)):
                audio_array[i] = int(audio_array[i] * self._volume)
            data = audio_array.tobytes()
        return data


def setup_slash_commands(bot):
    """Setup all slash commands"""
    
    # Music Commands Group
    @bot.tree.command(name="play", description="Phát nhạc từ YouTube")
    @app_commands.describe(query="Tên bài hát hoặc URL YouTube")
    async def play_slash(interaction: discord.Interaction, query: str):
        """Phát nhạc từ YouTube"""
        try:
            # Defer the response since this might take a while
            await interaction.response.defer()
            
            # Create a mock context for compatibility with existing functions
            class MockContext:
                def __init__(self, interaction):
                    self.guild = interaction.guild
                    self.channel = interaction.channel
                    self.author = interaction.user
                    self.message = interaction
                    
                async def send(self, content=None, embed=None):
                    if interaction.response.is_done():
                        return await interaction.followup.send(content=content, embed=embed)
                    else:
                        return await interaction.response.send_message(content=content, embed=embed)
            
            ctx = MockContext(interaction)
            
            # Ensure bot is in voice channel
            vc = await ensure_voice(ctx.message)
            
            # Get or create player
            player = get_player(ctx.guild.id)
            player.text_channel_id = ctx.channel.id
            
            # Show searching message
            await interaction.followup.send(f"🔍 **Đang tìm kiếm:** {query}")
            
            try:
                # Extract track info
                track = await ytdlp_extract(query, ctx.author.id)
                
                # Add to queue
                player.add_track(track)
                
                # Update message
                await interaction.followup.send(f"✅ **Đã thêm vào queue:** {track.title}")
                
                # Start playing if not already playing
                if not vc.is_playing():
                    asyncio.create_task(play_next(ctx.guild, vc, player))
                    
            except Exception as e:
                await interaction.followup.send(f"❌ **Lỗi:** {str(e)}")
                
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ **Lỗi:** {str(e)}")
            else:
                await interaction.followup.send(f"❌ **Lỗi:** {str(e)}")
    
    @bot.tree.command(name="skip", description="Bỏ qua bài hát hiện tại")
    async def skip_slash(interaction: discord.Interaction):
        """Bỏ qua bài hát hiện tại"""
        try:
            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                await interaction.response.send_message("❌ Bot không ở trong voice channel")
                return
            
            if vc.is_playing():
                # Stop current track and trigger next
                vc.stop()
                await interaction.response.send_message("⏭️ **Đã bỏ qua bài hát hiện tại**")
                
                # Get player and play next track
                player = get_player(interaction.guild.id)
                if player.queue:
                    await interaction.followup.send("🔄 **Đang chuyển sang bài tiếp theo...**")
                    asyncio.create_task(play_next(interaction.guild, vc, player))
                else:
                    await interaction.followup.send("📭 **Queue đã hết, không còn bài nào để phát**")
            else:
                await interaction.response.send_message("❌ Không có gì đang phát")
                
        except Exception as e:
            await interaction.response.send_message(f"❌ **Lỗi:** {str(e)}")
    
    @bot.tree.command(name="queue", description="Hiển thị queue nhạc")
    async def queue_slash(interaction: discord.Interaction):
        """Hiển thị queue nhạc"""
        try:
            player = get_player(interaction.guild.id)
            queue_info = player.get_queue_info()
            
            if player.now_playing:
                now_playing = f"🎵 **Đang phát:** {player.now_playing.title}\n\n"
            else:
                now_playing = ""
            
            await interaction.response.send_message(f"{now_playing}{queue_info}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ **Lỗi:** {str(e)}")
    
    @bot.tree.command(name="stop", description="Dừng phát nhạc và rời voice channel")
    async def stop_slash(interaction: discord.Interaction):
        """Dừng phát nhạc và rời voice channel"""
        try:
            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                await interaction.response.send_message("❌ Bot không ở trong voice channel")
                return
            
            # Clear queue and stop
            player = get_player(interaction.guild.id)
            player.clear_queue()
            player.skip_current()
            
            # Disconnect
            await vc.disconnect()
            await interaction.response.send_message("⏹️ **Đã dừng phát nhạc và rời voice channel**")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ **Lỗi:** {str(e)}")
    
    @bot.tree.command(name="volume", description="Điều chỉnh âm lượng (0-200%)")
    @app_commands.describe(level="Mức âm lượng từ 0 đến 200 (%)")
    async def volume_slash(interaction: discord.Interaction, level: int):
        """Điều chỉnh âm lượng (0-200%)"""
        try:
            if not 0 <= level <= 200:
                await interaction.response.send_message("❌ Âm lượng phải từ 0% đến 200%")
                return
            
            player = get_player(interaction.guild.id)
            # Convert percentage to decimal (0-2.0)
            volume_decimal = level / 100.0
            player.set_volume(volume_decimal)
            
            # Apply volume to currently playing audio if any
            vc = interaction.guild.voice_client
            if vc and vc.is_playing() and player.now_playing:
                # Use our custom volume control
                if hasattr(vc.source, 'volume'):
                    vc.source.volume = volume_decimal
                    await interaction.response.send_message(f"🔊 **Âm lượng đã được đặt thành:** {level}% (áp dụng ngay lập tức)")
                else:
                    # Fallback to FFmpeg method if source doesn't support volume
                    await apply_volume_from_current_position(vc, player, volume_decimal)
                    await interaction.response.send_message(f"🔊 **Âm lượng đã được đặt thành:** {level}% (đang áp dụng...)")
            else:
                await interaction.response.send_message(f"🔊 **Âm lượng đã được đặt thành:** {level}%")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ **Lỗi:** {str(e)}")
    
    # Admin Commands
    @bot.tree.command(name="ping", description="Kiểm tra độ trễ của bot")
    async def ping_slash(interaction: discord.Interaction):
        """Kiểm tra độ trễ của bot"""
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(f"🏓 **Pong!** Độ trễ: {latency}ms")
    
    @bot.tree.command(name="info", description="Thông tin về bot")
    async def info_slash(interaction: discord.Interaction):
        """Thông tin về bot"""
        embed = discord.Embed(
            title="🤖 **VnuTourBot**",
            description="Bot quản lý tour VNU với chức năng âm nhạc",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📊 **Thống kê**",
            value=f"Servers: {len(bot.guilds)}\nUsers: {len(bot.users)}",
            inline=True
        )
        
        embed.add_field(
            name="🏓 **Độ trễ**",
            value=f"{round(bot.latency * 1000)}ms",
            inline=True
        )
        
        embed.add_field(
            name="🐍 **Phiên bản**",
            value=f"discord.py {discord.__version__}",
            inline=True
        )
        
        embed.set_footer(text="VnuTourBot v1.0")
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="clear", description="Xóa tin nhắn (chỉ admin)")
    @app_commands.describe(amount="Số lượng tin nhắn cần xóa")
    @app_commands.default_permissions(manage_messages=True)
    async def clear_slash(interaction: discord.Interaction, amount: int):
        """Xóa tin nhắn (chỉ admin)"""
        try:
            if amount < 1 or amount > 100:
                await interaction.response.send_message("❌ Số lượng tin nhắn phải từ 1 đến 100")
                return
            
            # Defer response since this might take a while
            await interaction.response.defer(ephemeral=True)
            
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"🗑️ **Đã xóa {len(deleted)} tin nhắn**", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot không có quyền xóa tin nhắn", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ **Lỗi:** {str(e)}", ephemeral=True)
    
    # Help Command
    @bot.tree.command(name="help", description="Hiển thị hướng dẫn sử dụng bot")
    async def help_slash(interaction: discord.Interaction):
        """Hiển thị hướng dẫn sử dụng bot"""
        embed = discord.Embed(
            title="🤖 **VnuTourBot - Hướng dẫn sử dụng**",
            description="Bot quản lý tour VNU với các chức năng âm nhạc và quản lý trạm",
            color=0x00ff00
        )
        
        # Music commands
        embed.add_field(
            name="🎵 **Lệnh âm nhạc**",
            value=(
                "`/play <tên/URL>` - Phát nhạc\n"
                "`/skip` - Bỏ qua bài hát hiện tại\n"
                "`/queue` - Hiển thị queue nhạc\n"
                "`/stop` - Dừng phát nhạc\n"
                "`/volume <0-200>` - Điều chỉnh âm lượng"
            ),
            inline=False
        )
        
        # Admin commands
        embed.add_field(
            name="🔧 **Lệnh admin**",
            value=(
                "`/ping` - Kiểm tra độ trễ\n"
                "`/info` - Thông tin bot\n"
                "`/clear <số>` - Xóa tin nhắn"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 **Ghi chú**",
            value="Sử dụng `/` để xem tất cả các lệnh có sẵn",
            inline=False
        )
        
        embed.set_footer(text="VnuTourBot v1.0 - Slash Commands")
        await interaction.response.send_message(embed=embed)


# Helper functions (copied from music_commands.py)
async def apply_volume_from_current_position(vc: discord.VoiceClient, player, volume: float):
    """Apply volume immediately from current playback position"""
    try:
        # Get current track info
        track = player.now_playing
        if not track:
            return
        
        # Calculate current playback position
        current_time = 0
        if player.started_at:
            current_time = discord.utils.utcnow().timestamp() - player.started_at
        
        # Ensure current_time is not negative
        current_time = max(0, current_time)
        
        # Build FFmpeg options with seek to current position
        ffmpeg_opts = build_ffmpeg_options(track)
        
        # Add seek option to start from current position
        seek_option = f"-ss {current_time}"
        
        # Create new audio source with seek and volume
        source = discord.FFmpegPCMAudio(
            track.stream_url,
            before_options=f"{ffmpeg_opts} {seek_option}",
            options=f"-vn -af volume={volume}"
        )
        
        # Store new source
        player.current_source = source
        
        # Update start time to current position
        player.started_at = discord.utils.utcnow().timestamp() - current_time
        
        # Stop current playback first
        vc.stop()
        
        # Give more time for clean stop and cleanup
        await asyncio.sleep(0.1)
        
        # Cleanup old source if exists
        force_cleanup_ffmpeg_source(player.current_source)
        
        # Play with new volume from current position
        vc.play(source, after=lambda err: threading.Thread(target=lambda: asyncio.run(after_play_callback(err, player))).start())
        
    except Exception as e:
        print(f"[VOLUME POSITION ERROR] {e}")


async def play_next(guild, vc, player):
    """Play the next track in queue"""
    try:
        # Get next track
        track = player.get_next_track()
        if not track:
            return
        
        # Set as now playing
        player.now_playing = track
        player.started_at = discord.utils.utcnow().timestamp()
        
        # Build FFmpeg options
        ffmpeg_opts = build_ffmpeg_options(track)
        
        # Create audio source with current volume
        source = VolumeControlledAudioSource(
            track.stream_url,
            volume=player.volume,
            before_options=ffmpeg_opts,
            options="-vn"  # No volume filter needed, handled by our class
        )
        
        # Store source for cleanup
        player.current_source = source
        
        # Play audio with safe callback
        vc.play(source, after=lambda err: threading.Thread(target=lambda: asyncio.run(after_play_callback(err, player))).start())
        
        # Send now playing message with beautiful embed
        channel = guild.get_channel(player.text_channel_id)
        if channel:
            now_playing_embed = create_now_playing_embed(track)
            player.now_playing_msg = await channel.send(embed=now_playing_embed)
        
        # Create background task to handle track completion
        async def handle_track_completion():
            # Wait for completion
            await player.finished.wait()
            player.finished.clear()
            
            # When track finishes, update message to simple text
            if player.now_playing_msg:
                try:
                    await player.now_playing_msg.edit(content=f"✅ **Đã phát xong:** {track.title}", embed=None)
                except:
                    pass
            
            # Play next track if available
            if player.queue:
                await play_next(guild, vc, player)
            else:
                player.now_playing = None
                player.started_at = None
                player.now_playing_msg = None
        
        # Start background task (non-blocking)
        asyncio.create_task(handle_track_completion())
            
    except Exception as e:
        print(f"[PLAY NEXT ERROR] {e}")
        # Try to play next track
        if player.queue:
            await play_next(guild, vc, player)


def create_now_playing_embed(track):
    """Create a beautiful now playing embed"""
    embed = discord.Embed(
        title="🎵 **Đang phát**",
        description=f"**{track.title}**",
        color=0x00ff00
    )
    
    # Add artist info if available
    if hasattr(track, 'artist') and track.artist:
        embed.add_field(
            name="👤 **Nghệ sĩ**",
            value=track.artist,
            inline=True
        )
    
    # Add duration
    if hasattr(track, 'duration') and track.duration:
        duration_str = track.get_duration_str()
        embed.add_field(
            name="⏱️ **Thời lượng**",
            value=duration_str,
            inline=True
        )
    
    # Add uploader if available
    if hasattr(track, 'uploader') and track.uploader:
        embed.add_field(
            name="📺 **Kênh**",
            value=track.uploader,
            inline=True
        )
    
    # Add thumbnail if available
    if hasattr(track, 'thumbnail') and track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    
    embed.set_footer(text="🎶 VnuTourBot Music Player")
    return embed
