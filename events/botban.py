import discord
from discord.ext import commands

ROLE_ID_TO_BAN = 1439354601672282335
LOG_CHANNEL_ID = 1440055015711703242


class AutoBanOnRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Role was just added
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        added_roles = after_roles - before_roles

        # Check if the trap role was added
        if any(role.id == ROLE_ID_TO_BAN for role in added_roles):
            guild = after.guild

            # Ban the user
            try:
                await guild.ban(
                    after,
                    reason="Bot automatically banned due to receiving trap role."
                )
            except Exception as e:
                print(f"Failed to ban {after}: {e}")
                return

            # Log the event
            channel = guild.get_channel(LOG_CHANNEL_ID)
            if channel is not None:
                embed = discord.Embed(
                    title="🚫 Bot Detected & Auto-Banned",
                    description=(
                        f"**User:** {after.mention} (`{after.id}`)\n"
                        f"**Action:** Automatically banned\n"
                        f"**Reason:** Received bot-trap role"
                    ),
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=after.display_avatar.url)

                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print("AutoBanOnRole cog loaded.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoBanOnRole(bot))
