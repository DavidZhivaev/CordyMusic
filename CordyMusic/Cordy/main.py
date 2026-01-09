from disnake import (Activity, ActivityType, AllowedMentions, Intents,
                     Status)
from disnake.ext import commands
from core import Cordy

intents = Intents.default()
intents.voice_states = True

bot = Cordy(
    owner_ids=[326369659832107010],
    shard_count=4,
    allowed_mentions=AllowedMentions(
        everyone=False,
        replied_user=True,
        roles=False,
        users=True
    ),
    intents=intents,
    activity = Activity(name='New era of music bots', type=ActivityType.custom, state='New era of music bots'),
    status=Status.online,
    command_sync_flags=commands.CommandSyncFlags(
        allow_command_deletion = True,
        sync_commands = True,
        sync_commands_debug = True,
        sync_global_commands = True,
        sync_guild_commands=True
    ),
    enable_debug_events=True,
    chunk_guilds_at_startup=False
)

bot.run(bot.config.TOKEN)