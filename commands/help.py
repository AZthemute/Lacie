import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, List


class HelpView(discord.ui.View):

    def __init__(self, bot, cog_commands: Dict[str, List[str]]):
        super().__init__(timeout=180)
        self.bot = bot
        self.cog_commands = cog_commands
        self.current_page = "home"

        self.cog_info = {
            "commands": {"name": "General", "emoji": "⚙️"},
            "moderation": {"name": "Moderation", "emoji": "🛡️"},
            "xp": {"name": "XP & Leveling", "emoji": "⭐"},
            "sparkle": {"name": "Sparkle", "emoji": "✨"},
            "image": {"name": "Image", "emoji": "🖼️"},
            "suggestion": {"name": "Suggestions", "emoji": "💡"},
            "birthday": {"name": "Birthdays", "emoji": "🎂"},
            "embed": {"name": "Embed", "emoji": "📝"},
            "embeds": {"name": "Embeds", "emoji": "📜"},
            "profiles": {"name": "Profiles", "emoji": "👤"},
            "wordle": {"name": "Wordle", "emoji": "🟩"},
        }

        self.add_cog_buttons()

        home_button = discord.ui.Button(
            label="Home",
            emoji="🏠",
            style=discord.ButtonStyle.primary,
            custom_id="help_home",
            row=4
        )
        home_button.callback = self.show_home
        self.add_item(home_button)

    def add_cog_buttons(self):
        row = 0
        col = 0
        for cog_key in [
            "commands", "moderation", "xp", "sparkle",
            "image", "suggestion", "birthday",
            "embed", "embeds", "profiles", "wordle"
        ]:
            if cog_key in self.cog_commands and self.cog_commands[cog_key]:
                info = self.cog_info.get(cog_key, {"emoji": "📦", "name": cog_key.title()})

                button = discord.ui.Button(
                    label=info["name"],
                    emoji=info["emoji"],
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"help_{cog_key}",
                    row=row
                )

                def make_callback(cog_name=cog_key):
                    async def callback(interaction: discord.Interaction):
                        try:
                            await self.show_cog(interaction, cog_name)
                        except Exception as e:
                            print(f"Button callback error for {cog_name}: {e}")
                            import traceback
                            traceback.print_exc()
                            try:
                                await interaction.response.send_message(f"Error: {e}", ephemeral=True)
                            except:
                                pass
                    return callback

                button.callback = make_callback()
                self.add_item(button)

                col += 1
                if col >= 5:
                    col = 0
                    row += 1

    async def show_home(self, interaction: discord.Interaction):
        try:
            self.current_page = "home"
            embed = self.create_home_embed(interaction)
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    async def show_cog(self, interaction: discord.Interaction, cog_name: str):
        try:
            self.current_page = cog_name
            embed = self.create_cog_embed(interaction, cog_name)
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    def create_home_embed(self, interaction: discord.Interaction) -> discord.Embed:
        color = discord.Color.purple()
        try:
            embed_color_cog = self.bot.get_cog("EmbedColor")
            if embed_color_cog:
                color = embed_color_cog.get_user_color(interaction.user)
        except:
            pass

        embed = discord.Embed(
            title="🤖 Lacie Bot - Help",
            description=(
                "Welcome to Lacie! Use the buttons below to explore the different command categories.\n\n"
                "**💡 Found a bug or have an idea?**\n"
                "Use `/suggest` to report bugs or suggest new features! Your feedback helps improve the bot."
            ),
            color=color
        )

        embed.add_field(
            name="🔗 Links",
            value=(
                "• [GitHub Repository](https://github.com/Lilac-Rose/Lacie)\n"
                "• [Web Dashboard](https://bots.lilacrose.dev/lacie/)"
            ),
            inline=False
        )

        embed.set_footer(text="Created with 💜 by Lilac Aria Rose")
        return embed

    def create_cog_embed(self, interaction: discord.Interaction, cog_name: str) -> discord.Embed:
        info = self.cog_info.get(cog_name, {"emoji": "📦", "name": cog_name.title()})

        color = discord.Color.blue()
        try:
            embed_color_cog = self.bot.get_cog("EmbedColor")
            if embed_color_cog:
                color = embed_color_cog.get_user_color(interaction.user)
        except:
            pass

        embed = discord.Embed(
            title=f"{info['emoji']} {info['name']} Commands",
            description="Here are all the commands in this category:",
            color=color
        )

        if cog_name in self.cog_commands:
            commands_list = "\n".join(sorted(set(self.cog_commands[cog_name])))
            if len(commands_list) > 4096:
                chunks = []
                current_chunk = []
                current_length = 0
                for cmd in sorted(set(self.cog_commands[cog_name])):
                    if current_length + len(cmd) + 1 > 1024:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [cmd]
                        current_length = len(cmd)
                    else:
                        current_chunk.append(cmd)
                        current_length += len(cmd) + 1
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                for i, chunk in enumerate(chunks):
                    field_name = "Commands" if i == 0 else f"Commands (cont. {i+1})"
                    embed.add_field(name=field_name, value=chunk, inline=False)
            else:
                embed.description = commands_list
        else:
            embed.description = "No commands found in this category."

        embed.set_footer(
            text=f"Use the buttons to navigate • Total: {len(set(self.cog_commands.get(cog_name, [])))} commands"
        )
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Shows all available commands organized by category")
    async def help_command(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True)
            cog_commands = {}

            # Process slash commands safely
            for command in self.bot.tree.get_commands():
                cog = getattr(command, "binding", None)  # <-- FIX HERE
                if cog:
                    module = cog.__class__.__module__
                    folder = module.split(".")[0] if "." in module else "other"
                else:
                    folder = "other"

                if folder == "events":
                    continue

                cog_commands.setdefault(folder, [])
                cmd_desc = command.description or "No description"
                cog_commands[folder].append(f"`/{command.name}` - {cmd_desc}")

            # Process prefix commands
            for cmd_name, command in self.bot.all_commands.items():
                if command.name != cmd_name:
                    continue

                if command.cog:
                    module = command.cog.__class__.__module__
                    folder = module.split(".")[0] if "." in module else "other"
                else:
                    folder = "other"

                if folder == "events":
                    continue

                cog_commands.setdefault(folder, [])
                cmd_desc = command.help or command.brief or "No description"
                alias_text = f" (aliases: {', '.join(f'!{a}' for a in command.aliases)})" if command.aliases else ""
                cog_commands[folder].append(f"`!{command.name}`{alias_text} - {cmd_desc}")

            view = HelpView(self.bot, cog_commands)
            embed = view.create_home_embed(interaction)

            print(f"DEBUG: Found cogs: {list(cog_commands.keys())}")
            for cog_name, cmds in cog_commands.items():
                print(f"  {cog_name}: {len(set(cmds))} unique commands")

            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            import traceback
            error_msg = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_embed = discord.Embed(
                title="❌ Error in /help command",
                description=f"```py\n{error_msg[:4000]}```",
                color=discord.Color.red()
            )
            try:
                await interaction.followup.send(embed=error_embed)
            except:
                await interaction.response.send_message(embed=error_embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
