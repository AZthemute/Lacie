import math
import random
import time
import json
import discord
from discord.utils import get
from pathlib import Path

CONFIG_PATH = Path("/home/lilacrose/lilacrose.dev2.0/bots/lacie/xp_config.json")

def load_config():
    with CONFIG_PATH.open() as f:
        return json.load(f)

def get_multiplier(member, apply_multiplier=True):
    """Get XP multiplier for a member based on their roles"""
    if not apply_multiplier:
        return 1
    
    # Ensure we have a Member object with roles
    if not isinstance(member, discord.Member):
        return 1
    
    config = load_config()
    multipliers = config["MULTIPLIERS"]
    highest = 1
    
    for role in member.roles:
        if str(role.id) in multipliers:
            highest = max(highest, multipliers[str(role.id)])
    
    return highest

def xp_for_level(level: int) -> int:
    """Calculate total XP required to reach a given level"""
    config = load_config()
    curve = config.get("XP_CURVE", {"base": 1, "square": 50, "linear": 100, "divisor": 100})
    
    xp = (level ** 3 * curve["base"]) + (level ** 2 * curve["square"]) + (level * curve["linear"])
    xp = xp / curve["divisor"]
    return int(math.floor(xp / 100) * 100)

def random_xp() -> int:
    """Generate random XP amount within configured range"""
    config = load_config()
    xp_range = config.get("RANDOM_XP", {"min": 50, "max": 100})
    return random.randint(xp_range["min"], xp_range["max"])

def can_get_xp(last_message_time: int) -> bool:
    """Check if enough time has passed since last XP gain"""
    config = load_config()
    cooldown = config["COOLDOWN"]
    return (time.time() - last_message_time) >= cooldown

async def check_level_up(member, cur, conn, lifetime=True):
    """Check if member leveled up and grant role rewards"""
    # Ensure we have a Member object
    if not isinstance(member, discord.Member):
        return
    
    config = load_config()
    role_rewards = {int(k): int(v) for k, v in config["ROLE_REWARDS"].items()}
    
    cur.execute("SELECT xp, level FROM xp WHERE user_id = ?", (str(member.id),))
    row = cur.fetchone()
    if not row:
        return
    
    xp, level = row
    new_level = level
    
    while xp >= xp_for_level(new_level + 1):
        new_level += 1
    
    if new_level > level:
        cur.execute("UPDATE xp SET level = ? WHERE user_id = ?", (new_level, str(member.id)))
        conn.commit()
        
        if lifetime:
            # Grant all roles for levels they've reached
            for lvl, role_id in role_rewards.items():
                if new_level >= lvl:
                    role = get(member.guild.roles, id=role_id)
                    if role and role not in member.roles:
                        await member.add_roles(role)