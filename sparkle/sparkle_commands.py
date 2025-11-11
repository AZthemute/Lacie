import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import escape_markdown
from .database import get_db
import asyncio


class SparkleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sparkle_emojis = {
            "epic": "💫",
            "rare": "🌟",
            "regular": "✨"
        }
    
    # Create sparkle command group
    sparkle_group = app_commands.Group(name="sparkle", description="Sparkle tracking and information")
    
    @sparkle_group.command(name="check", description="Check your sparkle count or another user's")
    @app_commands.describe(user="The user to check sparkle count for (leave empty for yourself)")
    async def sparkle_check(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        
        def db_task():
            conn = get_db()
            cursor = conn.execute(
                """
                SELECT epic, rare, regular,
                    (epic + rare + regular) as total
                FROM sparkles
                WHERE server_id = ? AND user_id = ?
                """,
                (str(interaction.guild.id), str(user.id))
            )
            result = cursor.fetchone()
            conn.close()
            return result
        
        result = await asyncio.to_thread(db_task)
        
        if not result:
            await interaction.response.send_message(
                f"{user.display_name} has no sparkles yet!", 
                ephemeral=True
            )
            return
        
        epic, rare, regular, total = result
        embed = discord.Embed(
            title=f"{user.display_name}'s Sparkles",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(
            name="Totals",
            value=(
                f"{self.sparkle_emojis['epic']} **Epic:** {epic}\n"
                f"{self.sparkle_emojis['rare']} **Rare:** {rare}\n"
                f"{self.sparkle_emojis['regular']} **Regular:** {regular}\n"
                f"**Total:** {total}"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @sparkle_group.command(name="info", description="Learn about sparkles and how they work")
    async def sparkle_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ Sparkles ✨",
            description=(
                "Sparkles are **random reactions** that can appear on messages! "
                "Sometimes, when you send a message, you might get a sparkle reaction and a little notification.\n\n"
                "**Types of Sparkles:**\n"
                "✨ **Regular Sparkle** – Appears randomly (1/1,000 chance per message)\n"
                "🌟 **Rare Sparkle** – Appears less often (1/10,000 chance per message)\n"
                "💫 **Epic Sparkle** – Extremely rare! (1/100,000 chance per message)\n\n"
                "You can track your sparkles and compare with others using `/sparkle leaderboard`."
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Keep sending messages to try your luck!")
        
        await interaction.response.send_message(embed=embed)
    
    @sparkle_group.command(name="leaderboard", description="Show server sparkle random leaderbaord")
    @app_commands.describe(limit="Number of users to show (max 20, default 10)")
    async def sparkle_leaderboard(self, interaction: discord.Interaction, limit: int = 10):
        limit = max(1, min(20, limit))
        
        guild_member_ids = {str(member.id) for member in interaction.guild.members}
        
        if not guild_member_ids:
            await interaction.response.send_message(
                "This server has no members to display.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        def db_task():
            conn = get_db()
            placeholders = ",".join(["?"] * len(guild_member_ids))
            query = f"""
                SELECT user_id, epic, rare, regular,
                       (epic + rare + regular) as total
                FROM sparkles
                WHERE server_id = ? AND user_id IN ({placeholders})
                ORDER BY random()
                LIMIT ?
            """
            params = [str(interaction.guild.id), *guild_member_ids, limit]
            cursor = conn.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            return results
        
        results = await asyncio.to_thread(db_task)
        
        if not results:
            await interaction.followup.send(
                "No sparkle data available for members of this server.", 
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"✨ {escape_markdown(interaction.guild.name)} Random Sparkle Leaderboard",
            color=discord.Color.gold()
        )
        
        # Add medal emojis for top 3
        medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        
        for rank, (user_id, epic, rare, regular, total) in enumerate(results, 1):
            user = interaction.guild.get_member(int(user_id))
            display_name = escape_markdown(user.display_name) if user else f"Unknown User ({user_id})"
            
            # Add medal emoji for top 3
            rank_display = medal_emojis.get(rank, f"{rank}.")
            
            sparkles = (
                f"{self.sparkle_emojis['epic']} {epic} | "
                f"{self.sparkle_emojis['rare']} {rare} | "
                f"{self.sparkle_emojis['regular']} {regular} | "
                f"**Total:** {total}"
            )
            
            embed.add_field(
                name=f"{rank_display} {display_name}", 
                value=sparkles, 
                inline=False
            )
            
            # Set thumbnail to #1 user's avatar
            if rank == 1 and user:
                embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.set_footer(text="💫 Epic | 🌟 Rare | ✨ Regular")
        
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SparkleCommands(bot))