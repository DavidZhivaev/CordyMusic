import json
from os import listdir

from disnake import Guild
from disnake.ext import commands
from jishaku.modules import find_extensions_in
import json
from config import Config

from .classes.embeds import Embeds
import mafic

class Cordy(commands.AutoShardedInteractionBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        kwargs['config'] = Config()

        self.config = Config()

        self.ru_locale = None
        self.en_locale = None
        with open('./locale/ru.json') as json_file: self.ru_locale = json.load(json_file)
        with open('./locale/en.json') as json_file: self.en_locale = json.load(json_file)
        
        self.embeds = Embeds(self.config.DEFAULT_EMBED_COLOR)

        self.pool = mafic.NodePool(self)

        self.loop.create_task(self.add_nodes())

        for folder in listdir('cogs'):
            for cog in find_extensions_in(f'cogs/{folder}'):
                try:
                    self.load_extension(cog)
                    print(f'{cog} loaded!')
                except Exception as e:
                    print(f'{folder}.{cog} err on startup: {e}')
    
    async def get_locale(self, guild_id: int, key: str) -> str:
        data = await self.config.DB.guilds.find_one({'id': guild_id})
        lang = 'en' if not data else data['lang']
        return self.ru_locale[key] if lang == 'ru' else self.en_locale[key] # pyright: ignore[reportOptionalSubscript]

    async def add_nodes(self) -> None:
        for node in self.config.MUSIC_NODES:
            await self.pool.create_node(
                host=self.config.MUSIC_NODES[node]["host"],
                port=self.config.MUSIC_NODES[node]["port"],
                label=node,
                password=self.config.MUSIC_NODES[node]["password"]
            )

    async def get_stats(self) -> dict:
        return {"servers": len(self.guilds), "shards": self.shard_count, "members": len(self.users)}
    
    def available_nodes(self) -> int:
        return len([_ for _ in self.pool.nodes if _.available])
    
    async def on_ready(self) -> None:
        ...