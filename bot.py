import discord
import yt_dlp
import asyncio
import os
from discord import PCMVolumeTransformer, FFmpegPCMAudio

# Initialize intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Use discord.Client instead of commands.Bot
client = discord.Client(intents=intents)

# Music-related variables
queue = []
current_song = None


@client.event
async def on_ready():
    print(f"{client.user.name} is online and ready to groove!")


def yt_search(query):
    """Search for a YouTube video and return its details."""
    ydl_opts = {
        "format": "bestaudio",
        "quiet": True,
        "noplaylist": True,
        "default_search": "auto",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        results = ydl.extract_info(f"ytsearch:{query}", download=False)
        return results["entries"][0] if results["entries"] else None


async def download_song(song):
    """Download song audio using yt-dlp."""
    ydl_opts = {
        "format": "bestaudio",
        "quiet": True,
        "outtmpl": f"{song['id']}.webm",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([song["webpage_url"]])
    return f"{song['id']}.webm"


async def play_next(ctx, voice_client):
    """Plays the next song in the queue or fetches a similar one if the queue is empty."""
    global current_song
    if queue:
        current_song = queue.pop(0)
        file_path = await download_song(current_song)
        source = PCMVolumeTransformer(FFmpegPCMAudio(file_path))
        voice_client.play(source, after=lambda _: asyncio.run_coroutine_threadsafe(play_next(ctx, voice_client), client.loop))
        await ctx.send(f"🎶 Now playing: **{current_song['title']}**")
    else:
        # Auto-play a similar song
        if current_song:
            related_song = yt_search(current_song["title"] + " similar")
            if related_song:
                current_song = related_song
                file_path = await download_song(current_song)
                source = PCMVolumeTransformer(FFmpegPCMAudio(file_path))
                voice_client.play(source, after=lambda _: asyncio.run_coroutine_threadsafe(play_next(ctx, voice_client), client.loop))
                await ctx.send(f"Queue is empty! Playing something similar: **{current_song['title']}**")
            else:
                await ctx.send("🚫 No songs found to continue. Taking a break!")
        else:
            await ctx.send("The music queue is empty, and I couldn't find anything to play.")


@client.event
async def on_message(message):
    if client.user in message.mentions:
        content = message.content.replace(f"<@!{client.user.id}>", "").strip()
        if content.startswith("play"):
            query = content[5:].strip()
            if not query:
                await message.channel.send("❌ You need to tell me what to play!")
                return

            song = yt_search(query)
            if song:
                queue.append(song)
                await message.channel.send(f"🎵 Added to queue: **{song['title']}**")
                if not message.guild.voice_client or not message.guild.voice_client.is_playing():
                    # Join the channel and play the song
                    if not message.author.voice:
                        await message.channel.send("❌ You need to be in a voice channel for me to join!")
                        return
                    vc = await message.author.voice.channel.connect()
                    await play_next(message, vc)
            else:
                await message.channel.send("❌ Couldn't find any results for your query!")

        elif content.startswith("pause"):
            if message.guild.voice_client and message.guild.voice_client.is_playing():
                message.guild.voice_client.pause()
                await message.channel.send("⏸ Paused the music.")
            else:
                await message.channel.send("❌ I can't pause silence!")

        elif content.startswith("resume"):
            if message.guild.voice_client and message.guild.voice_client.is_paused():
                message.guild.voice_client.resume()
                await message.channel.send("▶️ Resumed the music.")
            else:
                await message.channel.send("❌ Nothing to resume!")

        elif content.startswith("skip"):
            if message.guild.voice_client and message.guild.voice_client.is_playing():
                message.guild.voice_client.stop()
                await message.channel.send("⏭ Skipping to the next track...")
            else:
                await message.channel.send("❌ There's nothing to skip right now!")

        elif content.startswith("queue"):
            if queue:
                response = "🎶 Upcoming tracks:\n" + "\n".join(
                    [f"{i+1}. {song['title']}" for i, song in enumerate(queue)]
                )
                await message.channel.send(response)
            else:
                await message.channel.send("🎵 The queue is empty. Add some tunes!")

        elif content.startswith("play previous"):
            if current_song:
                queue.insert(0, current_song)
                await message.channel.send(f"🔁 Replaying: **{current_song['title']}**")
                message.guild.voice_client.stop()
            else:
                await message.channel.send("❌ No previous song to play!")

        elif content.startswith("stop"):
            if message.guild.voice_client:
                await message.guild.voice_client.disconnect()
                await message.channel.send("🛑 Stopped the music and left the voice channel.")
            else:
                await message.channel.send("❌ I'm not in a voice channel to stop!")


# Get the token from the environment variable
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

if DISCORD_TOKEN:
    client.run(DISCORD_TOKEN)
else:
    print("Error: Discord Bot Token not set in environment variables.")
                    
