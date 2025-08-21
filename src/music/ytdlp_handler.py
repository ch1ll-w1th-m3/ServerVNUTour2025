"""
YouTube-DL handler for music extraction
"""
import re
import yt_dlp
from typing import Optional
from .track import Track
import asyncio


# URL regex pattern
URL_RE = re.compile(r"^(https?://)")


def is_url(s: str) -> bool:
    """Check if string is a valid URL"""
    return bool(URL_RE.match(s.strip()))


# YouTube-DL options
YTDLP_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch1",
    "skip_download": True,
    "source_address": "0.0.0.0",
}


async def ytdlp_extract(query: str, requested_by: int) -> Track:
    """Extract track information using yt-dlp"""
    try:
        # Prepare query
        q = query if is_url(query) else f"ytsearch1:{query}"
        ytdl = yt_dlp.YoutubeDL(YTDLP_OPTS)
        
        # Run extraction in executor to avoid blocking
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, lambda: ytdl.extract_info(q, download=False))
        
        if not info:
            raise RuntimeError("Không thể lấy thông tin video")
        
        # Handle search results
        if "entries" in info:
            if not info["entries"]:
                raise RuntimeError("Không tìm thấy video nào")
            info = info["entries"][0]
        
        # Extract track information
        title = info.get("title", "Unknown Title")
        stream_url = info.get("url") or info.get("webpage_url", "")
        page_url = info.get("webpage_url", "")
        duration = info.get("duration")
        
        # Get headers for streaming
        headers = {}
        if "http_headers" in info:
            headers = info["http_headers"]
        
        return Track(
            title=title,
            stream_url=stream_url,
            page_url=page_url,
            duration=duration,
            requested_by=requested_by,
            headers=headers
        )
        
    except Exception as e:
        raise RuntimeError(f"Lỗi khi xử lý video: {str(e)}")


def build_ffmpeg_options(track: Track) -> str:
    """Build FFmpeg command line options for audio streaming"""
    import shutil
    
    # Base options
    base_opts = [
        "-reconnect", "1",
        "-reconnect_streamed", "1", 
        "-reconnect_delay_max", "5",
        "-nostdin",
        "-rw_timeout", "15000000"  # ~15s timeout
    ]
    
    # Add headers if available
    if track.headers:
        headers_str = "".join(f"{k}: {v}\r\n" for k, v in track.headers.items())
        base_opts.extend([
            "-headers", f'"{headers_str}"'
        ])
        
        # Add user agent if available
        if "User-Agent" in track.headers:
            base_opts.extend(["-user_agent", f'"{track.headers["User-Agent"]}"'])
    
    return " ".join(base_opts)

