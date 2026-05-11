import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import time

# ===================== CONFIG =====================

TOKEN = os.getenv("TOKEN")

ALLOWED_GUILD_ID = 1503294314955145246
CHANNEL_ID = 1503294318469845076

ROBLOX_USERS = [
    "Nosniy",
    "yr6aa",
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

CHECK_INTERVAL = 3

# Roblox Rivals Universe ID
RIVALS_UNIVERSE_ID = 5600755405

# ===================== BOT SETUP =====================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

last_state = {}

# ===================== DISCORD VIEW =====================

from discord import ui, ButtonStyle

class JoinView(ui.View):
    def __init__(self, url):
        super().__init__(timeout=None)

        if url:
            self.add_item(
                ui.Button(
                    label="Join Server",
                    style=ButtonStyle.link,
                    url=url
                )
            )

# ===================== MESSAGE SENDER =====================

async def send_tracker_message(channel, username, display_name, server_id, place_id, joinable):
    start = time.time()

    join_url = None
    if joinable and server_id:
        join_url = f"https://www.roblox.com/games/start?placeId={place_id}&gameInstanceId={server_id}"

    text = f"""**Charm owner joined!**
{display_name} (@{username}) joined server `{server_id or "Unknown"}`

"""

    if join_url:
        text += "🟢 This server is joinable\n"
    else:
        text += "❌ This place isn't joinable\n"

    text += "ℹ️ Server name: Private Server\n"

    ms = int((time.time() - start) * 1000)
    text += f"\nFound in {ms} ms"

    view = JoinView(join_url)

    await channel.send(content=text, view=view)

# ===================== ROBLOX API =====================

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
        print("Channel not found")
        return

    async with aiohttp.ClientSession() as session:

        user_ids = {}

        # safe lookup (prevents Roblox blocking)
        for u in ROBLOX_USERS:
            try:
                uid = await get_user_id(session, u)
                print("LOOKUP:", u, "->", uid)

                if uid:
                    user_ids[u] = uid

                await asyncio.sleep(0.5)

            except Exception as e:
                print("Lookup error:", u, e)

        print("Tracker started...")

        while not bot.is_closed():
            for username, user_id in user_ids.items():
                try:
                    presence = await get_presence(session, user_id)

                    if not presence:
                        continue

                    is_in_game = presence["userPresenceType"] == 2
                    universe_id = presence.get("universeId")

                    key = username

                    if key not in last_state:
                        last_state[key] = False
                        continue

                    # 🟢 JOIN RIVALS ONLY
                    if (
                        is_in_game
                        and universe_id == RIVALS_UNIVERSE_ID
                        and not last_state[key]
                    ):
                        await send_tracker_message(
                            channel,
                            username,
                            username,
                            presence.get("gameId"),
                            17625359962,
                            presence.get("gameId") is not None
                        )

                    # 🔴 LEAVE
                    if not is_in_game and last_state[key]:
                        await channel.send(f"🔴 **{username} left Roblox Rivals**")

                    last_state[key] = is_in_game and universe_id == RIVALS_UNIVERSE_ID

                except Exception as e:
                    print(f"Error tracking {username}: {e}")

            await asyncio.sleep(CHECK_INTERVAL)

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(monitor())

@bot.event
async def on_guild_join(guild):
    if guild.id != ALLOWED_GUILD_ID:
        await guild.leave()

# ===================== RUN =====================

bot.run(TOKEN)
