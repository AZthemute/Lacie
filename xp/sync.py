import discord
from discord.ext import commands
from discord import app_commands
from moderation.loader import ModerationBase, ADMIN_ROLE_ID
from .database import get_db
from .utils import load_config, xp_for_level
from discord.utils import get
import traceback

class XPSync(commands.Cog):
    """Sync XP role rewards for users."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def sync_roles_for_user(self, member: discord.Member) -> tuple[int, list[str]]:
        """Sync roles for a member based on their lifetime XP level."""
        config = load_config()
        ROLE_REWARDS = {int(k): int(v) for k, v in config["ROLE_REWARDS"].items()}

        conn, cur = get_db("lifetime")
        cur.execute("SELECT level FROM xp WHERE user_id = ?", (str(member.id),))
        row = cur.fetchone()
        conn.close()

        if not row:
            return (0, [])

        level = row[0]
        roles_added = []

        for lvl, role_id in ROLE_REWARDS.items():
            if level >= lvl:
                role = get(member.guild.roles, id=role_id)
                if role and role not in member.roles:
                    # Check bot hierarchy
                    if member.guild.me.top_role <= role:
                        continue
                    try:
                        await member.add_roles(role)
                        roles_added.append(role.name)
                    except discord.Forbidden:
                        print(f"Cannot assign {role.name} to {member} - missing permissions")
                    except discord.HTTPException as e:
                        print(f"HTTP error assigning {role.name} to {member}: {e}")

        return (level, roles_added)

    @app_commands.command(name="sync", description="Sync your XP role rewards.")
    @app_commands.describe(user="[Admin only] The user to sync roles for.")
    async def sync(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ):
        try:
            await interaction.response.defer()  # Bot is thinking
            print(f"Deferred sync interaction for user {interaction.user.id}")

            # Fetch target member properly
            try:
                target_member = await interaction.guild.fetch_member(user.id) if user else await interaction.guild.fetch_member(interaction.user.id)
            except discord.NotFound:
                return await interaction.followup.send("User is not in this server.")
            except discord.HTTPException as e:
                return await interaction.followup.send(f"Error fetching member: {e}")

            # If syncing someone else, check admin role
            if user and user.id != interaction.user.id:
                try:
                    member = await interaction.guild.fetch_member(interaction.user.id)
                except Exception:
                    return await interaction.followup.send("Could not find your member object.")

                has_admin_role = any(role.id == ADMIN_ROLE_ID for role in member.roles)
                if not has_admin_role:
                    return await interaction.followup.send("You don't have permission to sync roles for other users.")

            # Sync roles
            level, roles_added = await self.sync_roles_for_user(target_member)
            if level == 0:
                await interaction.followup.send(f"{target_member.mention} has no lifetime XP recorded.")
            elif roles_added:
                await interaction.followup.send(
                    f"Synced roles for {target_member.mention} (Level {level})\n"
                    f"**Roles added:** {', '.join(roles_added)}"
                )
            else:
                await interaction.followup.send(
                    f"{target_member.mention} (Level {level}) already has all eligible role rewards."
                )
        except Exception as e:
            print(f"Error in sync command: {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Error syncing roles: {e}")
            except:
                # If followup fails, try to edit the original response
                try:
                    await interaction.edit_original_response(content=f"❌ Error syncing roles: {e}")
                except:
                    print("Could not send error message to user")

async def setup(bot: commands.Bot):
    await bot.add_cog(XPSync(bot))