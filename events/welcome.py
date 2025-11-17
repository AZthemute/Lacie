import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.debug_channel_id = 1424145004976275617
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        
        bot_trap_role_id = 1439354601672282335
        if any(role.id == bot_trap_role_id for role in member.roles):
            return
        
        # Welcome channel
        welcome_channel = self.bot.get_channel(876772600704020533)
        
        # Create DM embed
        dm_embed = discord.Embed(
            title="Welcome!",
            description="If you have any questions just ask. However if there are questions related to the game (either be Project Kat or Paper Lily) please refer to <#893371132596588544>, but preferably <#1066672893959884860> if they contain any kind of in-game information that could be considered a spoiler for those who haven't played it.\n\nAnd please enjoy your stay!",
            color=discord.Color.blurple()
        )
        dm_embed.set_footer(text=f"Joined {member.guild.name}")
        dm_embed.timestamp = discord.utils.utcnow()
        
        # Try to send DM
        try:
            await member.send(embed=dm_embed)
            dm_success = True
        except discord.Forbidden:
            dm_success = False
        except discord.HTTPException as e:
            dm_success = False
        
        # Send welcome message in channel
        if welcome_channel:
            if dm_success:
                await welcome_channel.send(f"Welcome {member.mention} to the server!")
            else:
                await welcome_channel.send(f"Welcome {member.mention} to the server! I couldn't DM you the welcome message, so <@692683410132566016> will do that")

async def setup(bot):
    await bot.add_cog(Welcome(bot))