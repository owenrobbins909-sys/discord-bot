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

# Role ID to ping when someone joins (set to None to disable)
PING_ROLE_ID = None  # e.g. 1234567890123456789

ROBLOX_USERS = [
    "Nosniy","yr6aa","SenseiWarrior","nekoanims","CarbonMeister","Bandites",
    "Blizmid","DVwastaken","TanqR","BobbVX","PixelCat5","SubToMiniBloxia",
    "enriquebruv","chexworldwide","EHoopie","h0ppy819","ShadowTrojan",
    "Brian1KB","GreatGuyBoom","swaglord_KAYE","Karfulol","Khxyri","viecti",
    "SharkTactics","D_reamz","RealApplino","8sty","a2rix","philhood",
    "DunkinMud","KaiMemory","AtDarktru","SniperDude9167","MiloBloxin",
    "its_WE1RD","kashycod","ReallyCruz","StefanBloxxxxx"
]

# Roblox Rivals place ID (used for join link)
RIVALS_PLACE_ID = 17625359962  # Update if needed

CHECK_INTERVAL = 3

# ===================== BOT =====================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

last_state = {}  # username -> bool (in game or not)
user_display_names = {}  # username -> display name

# ===================== ROBLOX API =====================

async def get_user_info(session, username):
    """Returns (user_id, display_name) or (None, None)"""
    url = "https://users.roblox.com/v1/usernames/users"
    try:
        async with session.post(url, json={"usernames": [username], "excludeBannedUsers": True}) as r:
            data = await r.json()
            if not data.get("data"):
                return None, None
            user = data["data"][0]
            return user["id"], user.get("displayName", username)
    except Exception as e:
        print(f"get_user_info error for {username}: {e}")
        return None, None


async def get_presence(session, user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    try:
        async with session.post(url, json={"userIds": [user_id]}) as r:
            data = await r.json()
            presences = data.get("userPresences")
            if not presences:
                return None
            return presences[0]
    except Exception as e:
        print(f"get_presence error for {user_id}: {e}")
        return None


async def get_avatar_thumbnail(session, user_id):
    """Returns avatar headshot URL or None"""
    url = (
        f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    )
    try:
        async with session.get(url) as r:
            data = await r.json()
            items = data.get("data", [])
            if items and items[0].get("imageUrl"):
                return items[0]["imageUrl"]
    except Exception as e:
        print(f"get_avatar_thumbnail error: {e}")
    return None


async def get_game_name(session, place_id):
    """Returns game/universe name or None"""
    try:
        # First get universe ID from place ID
        async with session.get(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
        ) as r:
            data = await r.json()
            universe_id = data.get("universeId")
        if not universe_id:
            return None
        # Then get game details
        async with session.get(
            f"https://games.roblox.com/v1/games?universeIds={universe_id}"
        ) as r:
            data = await r.json()
            games = data.get("data", [])
            if games:
                return games[0].get("name")
    except Exception as e:
        print(f"get_game_name error: {e}")
    return None

# ===================== DISCORD MESSAGES =====================

async def send_join_message(channel, username, display_name, presence, avatar_url, ping_role_id, elapsed_ms):
    server_id = presence.get("gameId") or presence.get("rootPlaceId")
    place_id = presence.get("placeId")
    game_instance_id = presence.get("gameId")

    # Build join link
    join_url = None
    if place_id and game_instance_id:
        join_url = (
            f"https://www.roblox.com/games/start?placeId={place_id}"
            f"&gameInstanceId={game_instance_id}"
        )

    # Ping text
    ping_text = f"<@&{ping_role_id}> " if ping_role_id else ""
    content = f"{ping_text}**{username}** (@{display_name}) is playing Rivals!"

    # Build embed
    embed = discord.Embed(
        title="Charm owner joined!",
        color=0x57F287,  # green
    )

    description_lines = [
        f"**{username}** (@{display_name}) joined server",
        f"`{server_id or 'Unknown'}`",
        "",
    ]

    if join_url:
        description_lines.append("🟢 This place is joinable")
    else:
        description_lines.append("❌ This place isn't joinable")

    description_lines.append("ℹ️ Server name: Private Server")
    description_lines.append(f"\nFound in **{elapsed_ms} ms**")

    embed.description = "\n".join(description_lines)

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.set_footer(text="Charm Tracker")

    # Build view with join button if joinable
    view = discord.ui.View()
    if join_url:
        view.add_item(
            discord.ui.Button(
                label="Join Server",
                style=discord.ButtonStyle.link,
                url=join_url,
            )
        )
    view.add_item(
        discord.ui.Button(
            label="View Profile",
            style=discord.ButtonStyle.link,
            url=f"https://www.roblox.com/users/search?keyword={username}",
        )
    )

    await channel.send(content=content, embed=embed, view=view)


async def send_leave_message(channel, username, display_name, avatar_url, elapsed_ms):
    content = f"**{username}** (@{display_name}) left Rivals."

    embed = discord.Embed(
        title="Charm owner left!",
        color=0xED4245,  # red
    )

    embed.description = (
        f"**{username}** (@{display_name}) left Rivals.\n\n"
        f"Found in **{elapsed_ms} ms**"
    )

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.set_footer(text="Charm Tracker")

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="View Profile",
            style=discord.ButtonStyle.link,
            url=f"https://www.roblox.com/users/search?keyword={username}",
        )
    )

    await channel.send(content=content, embed=embed, view=view)

# ===================== MONITOR =====================

async def monitor():
    await bot.wait_until_ready()

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("❌ Channel not found. Check CHANNEL_ID.")
        return

    async with aiohttp.ClientSession() as session:

        # Resolve all usernames -> IDs and display names
        user_ids = {}
        avatar_urls = {}

        for username in ROBLOX_USERS:
            try:
                uid, display_name = await get_user_info(session, username)
                print(f"LOOKUP: {username} -> id={uid}, display={display_name}")
                if uid:
                    user_ids[username] = uid
                    user_display_names[username] = display_name or username
                    # Pre-fetch avatar
                    avatar_urls[username] = await get_avatar_thumbnail(session, uid)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Lookup error for {username}: {e}")

        print(f"✅ Tracker running for {len(user_ids)} users...")

        while not bot.is_closed():
            for username, user_id in user_ids.items():
                try:
                    start = time.time()
                    presence = await get_presence(session, user_id)

                    if presence is None:
                        continue

                    # Only trigger on Rivals (check place ID matches)
                    place_id = presence.get("placeId")
                    is_in_rivals = (
                        presence.get("userPresenceType") == 2
                        and place_id == RIVALS_PLACE_ID
                    )

                    elapsed_ms = int((time.time() - start) * 1000)
                    display_name = user_display_names.get(username, username)
                    avatar_url = avatar_urls.get(username)

                    # Skip first-seen (initialise state silently)
                    if username not in last_state:
                        last_state[username] = is_in_rivals
                        continue

                    # JOIN
                    if is_in_rivals and not last_state[username]:
                        print(f"🟢 {username} joined Rivals")
                        await send_join_message(
                            channel,
                            username,
                            display_name,
                            presence,
                            avatar_url,
                            PING_ROLE_ID,
                            elapsed_ms,
                        )

                    # LEAVE
                    elif not is_in_rivals and last_state[username]:
                        print(f"🔴 {username} left Rivals")
                        await send_leave_message(
                            channel,
                            username,
                            display_name,
                            avatar_url,
                            elapsed_ms,
                        )

                    last_state[username] = is_in_rivals

                except Exception as e:
                    print(f"Error tracking {username}: {e}")

            await asyncio.sleep(CHECK_INTERVAL)

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    bot.loop.create_task(monitor())


@bot.event
async def on_guild_join(guild):
    if guild.id != ALLOWED_GUILD_ID:
        await guild.leave()

# ===================== RUN =====================

bot.run(TOKEN)
