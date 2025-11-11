import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, timedelta, timezone
import re
from pathlib import Path


def parse_timeframe(timeframe: str) -> timedelta:
    """Parse strings like '1h', '2d', '3w', '30m' into timedelta."""
    pattern = r"(\d+)\s*(s|m|h|d|w)"
    match = re.fullmatch(pattern, timeframe.strip().lower())
    if not match:
        raise ValueError("Invalid time format. Use something like '10m', '2h', '3d', or '1w'.")

    value, unit = match.groups()
    value = int(value)
    match unit:
        case "s":
            return timedelta(seconds=value)
        case "m":
            return timedelta(minutes=value)
        case "h":
            return timedelta(hours=value)
        case "d":
            return timedelta(days=value)
        case "w":
            return timedelta(weeks=value)
    raise ValueError("Invalid time unit.")


class ReminderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ✅ Database will be stored next to this Python file
        self.db_path = Path(__file__).parent / "reminders.db"

    async def setup_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    remind_at TEXT
                )"""
            )
            await db.commit()

    async def cog_load(self):
        """Called automatically when the cog is added — safe place to start background tasks."""
        await self.setup_database()
        if not self.check_reminders.is_running():
            self.check_reminders.start()

    @app_commands.command(name="remind", description="Set a reminder and get a DM when it's time.")
    async def remind(self, interaction: discord.Interaction, timeframe: str, reminder: str):
        """Example: /remind 1h Take a break"""
        try:
            delta = parse_timeframe(timeframe)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

        remind_at = datetime.now(timezone.utc) + delta
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO reminders (user_id, message, remind_at) VALUES (?, ?, ?)",
                (interaction.user.id, reminder, remind_at.isoformat()),
            )
            await db.commit()

        await interaction.response.send_message(
            f"Got it! I'll DM you about **'{reminder}'** in {timeframe}.", ephemeral=True
        )

    @app_commands.command(name="reminders", description="View your active reminders.")
    async def reminders(self, interaction: discord.Interaction):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT message, remind_at FROM reminders WHERE user_id = ? ORDER BY remind_at",
                (interaction.user.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "You have no active reminders!", ephemeral=True
            )

        embed = discord.Embed(
            title="Your Reminders",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        for message, remind_at in rows:
            remind_time = datetime.fromisoformat(remind_at).strftime("%Y-%m-%d %H:%M UTC")
            embed.add_field(name=message, value=f"⏰ {remind_time}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        """Runs every minute, checks and delivers reminders."""
        now = datetime.now(timezone.utc)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, user_id, message FROM reminders WHERE remind_at <= ?",
                (now.isoformat(),),
            ) as cursor:
                reminders_due = await cursor.fetchall()

            for reminder_id, user_id, message in reminders_due:
                user = self.bot.get_user(user_id)
                if user:
                    try:
                        await user.send(f"⏰ **Reminder:** {message}")
                    except discord.Forbidden:
                        pass  # user has DMs disabled or bot blocked

                await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            await db.commit()

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ReminderCog(bot))
