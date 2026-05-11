import discord
from discord.ext import commands
import aiohttp
import asyncio

# ===================== CONFIG =====================

import os
TOKEN = os.getenv("TOKEN")

ALLOWED_GUILD_ID = 1503294314955145246
CHANNEL_ID = 1503294318469845076

ROBLOX_USERS = [
    "yr6aa",
    "Nosniy",
    "SenseiWarrior",
    "nekoanims",
    "CarbonMeister",
    "Bandites",
    "Blizmid",
    "DVwastaken",
    "TanqR",
    "BobbVX",
    "PixelCat5",
    "SubToMiniBloxia",
    "enriquebruv",
    "chexworldwide",
    "EHoopie",
    "h0ppy819",
    "ShadowTrojan",
    "Brian1KB",
    "GreatGuyBoom",
    "swaglord_KAYE",
    "Karfulol",
    "Khxyri",
    "viecti",
    "SharkTactics",
    "D_reamz",
    "RealApplino",
    "8sty",
    "a2rix",
    "philhood",
    "DunkinMud",
    "KaiMemory",
    "AtDarktru",
    "SniperDude9167",
    "MiloBloxin",
    "its_WE1RD",
    "kashycod",
    "ReallyCruz",
    "StefanBloxxxxx"
]

CHECK_INTERVAL = 3  # seconds (lower = faster but more risk of rate limits)

RIVALS_PLACE_ID = 17625359962

# ===================== BOT SETUP =====================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

last_state = {}

# ===================== ROBLOX FUNCTIONS =====================

async def get_user_id(session, username):
    url = "https://users.roblox.com/v1/usernames/users"
    async with session.post(url, json={"usernames": [username]}) as r:
        data = await r.json()
        if not data.get("data"):
            return None
        return data["data"][0]["id"]

async def get_presence(session, user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    async with session.post(url, json={"userIds": [user_id]}) as r:
        data = await r.json()
        return data["userPresences"][0]

# ===================== MONITOR LOOP =====================

async def monitor():
    await bot.wait_until_ready()

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("Channel not found. Check CHANNEL_ID.")
        return

    async with aiohttp.ClientSession() as session:

        # cache user IDs
        user_ids = {}
        for u in ROBLOX_USERS:
            uid = await get_user_id(session, u)
            if uid:
                user_ids[u] = uid

        while not bot.is_closed():
            for username, user_id in user_ids.items():
                try:
                    presence = await get_presence(session, user_id)

                    if not presence:
                        continue

                    is_in_game = presence["userPresenceType"] == 2
                    place_id = presence.get("placeId")

                    key = username

                    if key not in last_state:
                        last_state[key] = is_in_game
                        continue

                    # JOINED RIVALS
                    if is_in_game and not last_state[key]:
                        if place_id == RIVALS_PLACE_ID:
                            await channel.send(f"🟢 **{username} joined Roblox Rivals**")

                    # LEFT GAME
                    if not is_in_game and last_state[key]:
                        await channel.send(f"🔴 **{username} left Roblox Rivals**")

                    last_state[key] = is_in_game

                except Exception as e:
                    print(f"Error tracking {username}: {e}")

            await asyncio.sleep(CHECK_INTERVAL)

# ===================== DISCORD EVENTS =====================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # server lock (your privacy requirement)
    for guild in bot.guilds:
        if guild.id != ALLOWED_GUILD_ID:
            await guild.leave()

    bot.loop.create_task(monitor())

@bot.event
async def on_guild_join(guild):
    if guild.id != ALLOWED_GUILD_ID:
        await guild.leave()

# ===================== RUN BOT =====================

bot.run(TOKEN)
