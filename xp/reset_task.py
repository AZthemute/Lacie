from discord.ext import tasks, commands
from datetime import datetime, timezone
from .database import reset_leaderboard, get_last_reset
import calendar

class ResetTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_resets.start()
    
    def cog_unload(self):
        self.check_resets.cancel()
    
    @tasks.loop(minutes=1)
    async def check_resets(self):
        """Check if any leaderboards need to be reset."""
        now = datetime.now(timezone.utc)
        current_time = int(now.timestamp())
        
        # Daily reset - at midnight UTC
        if self.should_reset_daily(now):
            last_reset = get_last_reset("daily")
            # Check if we haven't reset today yet
            last_reset_date = datetime.fromtimestamp(last_reset, timezone.utc).date() if last_reset > 0 else None
            if last_reset_date != now.date():
                reset_leaderboard("daily")
                print(f"[XP System] Daily leaderboard reset at {now}")
        
        # Weekly reset - Sunday at midnight UTC
        if self.should_reset_weekly(now):
            last_reset = get_last_reset("weekly")
            last_reset_week = datetime.fromtimestamp(last_reset, timezone.utc).isocalendar()[1] if last_reset > 0 else None
            current_week = now.isocalendar()[1]
            if last_reset_week != current_week:
                reset_leaderboard("weekly")
                print(f"[XP System] Weekly leaderboard reset at {now}")
        
        # Monthly reset - Last day of month at midnight UTC
        if self.should_reset_monthly(now):
            last_reset = get_last_reset("monthly")
            last_reset_month = datetime.fromtimestamp(last_reset, timezone.utc).month if last_reset > 0 else None
            if last_reset_month != now.month:
                reset_leaderboard("monthly")
                print(f"[XP System] Monthly leaderboard reset at {now}")
    
    def should_reset_daily(self, now):
        """Check if it's time for daily reset (00:00 UTC)."""
        return now.hour == 0 and now.minute == 0
    
    def should_reset_weekly(self, now):
        """Check if it's time for weekly reset (Sunday 00:00 UTC)."""
        # weekday() returns 6 for Sunday
        return now.weekday() == 6 and now.hour == 0 and now.minute == 0
    
    def should_reset_monthly(self, now):
        """Check if it's time for monthly reset (last day of month 00:00 UTC)."""
        # Get last day of current month
        last_day = calendar.monthrange(now.year, now.month)[1]
        return now.day == last_day and now.hour == 0 and now.minute == 0
    
    @check_resets.before_loop
    async def before_check_resets(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

async def setup(bot):
    """Setup function to add the reset task cog."""
    await bot.add_cog(ResetTask(bot))