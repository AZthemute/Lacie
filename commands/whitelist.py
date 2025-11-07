import discord
from discord import app_commands
from discord.ext import commands
import json
import os

WHITELIST_FILE = "whitelist.json"
ADMIN_ROLE_NAME = "Ritual Member"

def load_whitelist():
    if not os.path.exists(WHITELIST_FILE):
        return {
            "Vanilla": {"pending": [], "whitelisted": []},
            "Modded": {"pending": [], "whitelisted": []},
            "Both": {"pending": [], "whitelisted": []}
        }
    with open(WHITELIST_FILE, "r") as f:
        return json.load(f)

def save_whitelist(data):
    with open(WHITELIST_FILE, "w") as f:
        json.dump(data, f, indent=4)

def normalize_username(username: str) -> str:
    """Normalize Minecraft username to prevent case-sensitivity issues."""
    return username.strip()

def has_admin_role(interaction: discord.Interaction) -> bool:
    """Check if user has admin permissions."""
    return any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles)

class WhitelistRequest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- /whitelistrequest ---
    @app_commands.command(name="whitelistrequest", description="Request to be whitelisted on a Minecraft server.")
    @app_commands.describe(server="Select which server to request for", username="Your Minecraft username")
    @app_commands.choices(server=[
        app_commands.Choice(name="Vanilla", value="Vanilla"),
        app_commands.Choice(name="Modded", value="Modded"),
        app_commands.Choice(name="Both", value="Both"),
    ])
    async def whitelist_request(self, interaction: discord.Interaction, server: app_commands.Choice[str], username: str):
        data = load_whitelist()
        server_key = server.value
        username = normalize_username(username)

        # Validate username (basic check)
        if len(username) < 3 or len(username) > 16 or not username.replace("_", "").isalnum():
            await interaction.response.send_message(
                f"⚠️ Invalid Minecraft username. Must be 3-16 characters (letters, numbers, underscores only).",
                ephemeral=True
            )
            return

        # Check all servers for existing requests/whitelists
        servers_to_check = ["Vanilla", "Modded", "Both"] if server_key == "Both" else [server_key]
        
        for s in servers_to_check:
            if username in data[s]["pending"]:
                await interaction.response.send_message(
                    f"⚠️ `{username}` already has a pending whitelist request for {s}.",
                    ephemeral=True
                )
                return
            if username in data[s]["whitelisted"]:
                await interaction.response.send_message(
                    f"⚠️ `{username}` is already whitelisted on {s}.",
                    ephemeral=True
                )
                return

        # Add request to appropriate server(s)
        if server_key == "Both":
            data["Vanilla"]["pending"].append(username)
            data["Modded"]["pending"].append(username)
        else:
            data[server_key]["pending"].append(username)
        
        save_whitelist(data)

        await interaction.response.send_message(
            f"📩 Whitelist request for `{username}` added to **{server.name}**.",
            ephemeral=False
        )

    # --- /listwhitelist ---
    @app_commands.command(name="listwhitelist", description="List whitelist requests and whitelisted players.")
    @app_commands.describe(status="Show pending or whitelisted users", server="Filter by server")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Pending", value="pending"),
            app_commands.Choice(name="Whitelisted", value="whitelisted"),
        ],
        server=[
            app_commands.Choice(name="Vanilla", value="Vanilla"),
            app_commands.Choice(name="Modded", value="Modded"),
            app_commands.Choice(name="Both", value="Both"),
        ],
    )
    async def list_whitelist(
        self,
        interaction: discord.Interaction,
        status: app_commands.Choice[str] = None,
        server: app_commands.Choice[str] = None
    ):
        data = load_whitelist()
        msg = "📋 **Whitelist Requests**\n\n"

        servers_to_show = [server.value] if server else ["Vanilla", "Modded"]
        status_to_show = [status.value] if status else ["pending", "whitelisted"]

        for s in servers_to_show:
            msg += f"**{s} Server:**\n"
            for st in status_to_show:
                users = data[s][st]
                if users:
                    msg += f"  • **{st.title()}**: {', '.join(users)}\n"
                else:
                    msg += f"  • **{st.title()}**: *(none)*\n"
            msg += "\n"

        await interaction.response.send_message(msg, ephemeral=False)

    # --- /markwhitelisted ---
    @app_commands.command(name="markwhitelisted", description="[ADMIN] Mark a pending user as whitelisted.")
    @app_commands.describe(server="Select which server", username="Minecraft username to mark as whitelisted")
    @app_commands.choices(server=[
        app_commands.Choice(name="Vanilla", value="Vanilla"),
        app_commands.Choice(name="Modded", value="Modded"),
        app_commands.Choice(name="Both", value="Both"),
    ])
    async def mark_whitelisted(self, interaction: discord.Interaction, server: app_commands.Choice[str], username: str):
        if not has_admin_role(interaction):
            await interaction.response.send_message("⛔ You need the Admin role to use this command.", ephemeral=True)
            return

        data = load_whitelist()
        server_key = server.value
        username = normalize_username(username)

        servers_to_update = ["Vanilla", "Modded"] if server_key == "Both" else [server_key]
        updated = []

        for s in servers_to_update:
            if username in data[s]["pending"]:
                data[s]["pending"].remove(username)
                if username not in data[s]["whitelisted"]:
                    data[s]["whitelisted"].append(username)
                updated.append(s)

        if not updated:
            await interaction.response.send_message(
                f"⚠️ `{username}` is not pending for {server.name}.",
                ephemeral=True
            )
            return

        save_whitelist(data)
        servers_str = " and ".join(updated)
        await interaction.response.send_message(
            f"✅ `{username}` has been marked as whitelisted on **{servers_str}**.",
            ephemeral=False
        )

    # --- /removewhitelist ---
    @app_commands.command(name="removewhitelist", description="[ADMIN] Remove a user from whitelist or reject a request.")
    @app_commands.describe(
        server="Select which server",
        username="Minecraft username to remove",
        remove_from="Remove from pending or whitelisted list"
    )
    @app_commands.choices(
        server=[
            app_commands.Choice(name="Vanilla", value="Vanilla"),
            app_commands.Choice(name="Modded", value="Modded"),
            app_commands.Choice(name="Both", value="Both"),
        ],
        remove_from=[
            app_commands.Choice(name="Pending", value="pending"),
            app_commands.Choice(name="Whitelisted", value="whitelisted"),
        ]
    )
    async def remove_whitelist(
        self,
        interaction: discord.Interaction,
        server: app_commands.Choice[str],
        username: str,
        remove_from: app_commands.Choice[str]
    ):
        if not has_admin_role(interaction):
            await interaction.response.send_message("⛔ You need the Admin role to use this command.", ephemeral=True)
            return

        data = load_whitelist()
        server_key = server.value
        username = normalize_username(username)
        list_type = remove_from.value

        servers_to_update = ["Vanilla", "Modded"] if server_key == "Both" else [server_key]
        removed = []

        for s in servers_to_update:
            if username in data[s][list_type]:
                data[s][list_type].remove(username)
                removed.append(s)

        if not removed:
            await interaction.response.send_message(
                f"⚠️ `{username}` is not in the {list_type} list for {server.name}.",
                ephemeral=True
            )
            return

        save_whitelist(data)
        servers_str = " and ".join(removed)
        await interaction.response.send_message(
            f"🗑️ `{username}` has been removed from the {list_type} list on **{servers_str}**.",
            ephemeral=False
        )

async def setup(bot):
    await bot.add_cog(WhitelistRequest(bot))