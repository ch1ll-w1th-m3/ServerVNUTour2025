"""
VnuTourBot - Discord Bot for VNU Tour Management
Main entry point
"""
import asyncio
from src.bot import VnuTourBot


def main():
    """Main function"""
    try:
        # Create and run bot
        bot = VnuTourBot()
        print("[MAIN] Khởi động VnuTourBot...")
        bot.run_bot()
        
    except KeyboardInterrupt:
        print("\n[MAIN] Bot đã được dừng bởi người dùng")
    except Exception as e:
        print(f"[MAIN] Lỗi khởi động bot: {e}")
        raise


if __name__ == '__main__':
    main()