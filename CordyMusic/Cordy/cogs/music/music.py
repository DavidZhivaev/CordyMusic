from datetime import datetime

from disnake import (ApplicationCommandInteraction, Embed, Guild,
                     MessageInteraction, ModalInteraction, SelectOption, TextChannel,
                     TextInputStyle, Member, User)
from disnake.ext import commands
from disnake.ui import Button, Modal, Select, TextInput, View

from core.bot import Cordy
from toolpack.formats import (format_millis_to_time, format_time_to_millis,
                              generate_random_string, code_text, decode_text)
import mafic
import asyncio
from core.classes import CordySong

class MusicCog(commands.Cog):
    def __init__(self, bot: Cordy) -> None:
        self.bot = bot
        self.bot.loop.create_task(self.clear_cache())

    async def clear_cache(self) -> None:
        await self.bot.wait_until_ready()
        await self.bot.config.DB.drop_collection("events_cache") if "events_cache" in await self.bot.config.DB.list_collection_names() else True
        while True:
            await self.bot.config.DB.search_cache.delete_many({'search_at': {'$lt': round(datetime.now().timestamp())-2}})
            await asyncio.sleep(30)
    
    async def add_song(self, guild_id: int, member: Member | User, channel: TextChannel, song: mafic.Track) -> int:
        if await self.bot.config.DB.queue.count_documents({'id': guild_id}) == 0:
            await self.bot.config.DB.queue.insert_one({'id': guild_id, 'loop': 'n', 'position_now': 0, 'channel': channel.id, 'last_message': 0, 'songs': [{'title': code_text(song.title), 'id': song.uri, 'put': member.id, 'source': 'sc' if song.source == 'soundcloud' else 'ym', 'custom_id': generate_random_string(15)}]})
            return 1
        data = (await self.bot.config.DB.queue.find_one({'id': guild_id}))['songs'] # pyright: ignore[reportOptionalSubscript]
        if len(data) == 0:
            await self.bot.config.DB.queue.update_one({'id': guild_id}, {'$set': {'songs': [{'title': code_text(song.title), 'id': song.uri, 'put': member.id, 'source': 'sc' if song.source == 'soundcloud' else 'ym', 'custom_id': generate_random_string(15)}]}})
            return 1
        await self.bot.config.DB.queue.update_one({'id': guild_id}, {'$push': {'songs': {'title': code_text(song.title), 'id': song.uri, 'put': member.id, 'source': 'sc' if song.source == 'soundcloud' else 'ym', 'custom_id': generate_random_string(15)}}})
        return len(data)+1
    
    @commands.Cog.listener()
    async def on_track_end(self, event: mafic.TrackEndEvent):
        guild: Guild = event.player.channel.guild
        player: mafic.Player = event.player

        data = await self.bot.config.DB.queue.find_one({'id': guild.id})
        if not data: return await guild.voice_client.disconnect(force=True)
        
        channel = guild.get_channel(data['channel'])

        async def send_message(text: str, guild_id: int, replace: bool = False, is_embed: bool = False, track: mafic.Track = None, put_by: int = None) -> None:
            if channel != None:
                if data['last_message'] != 0:
                    try:
                        message = await channel.fetch_message(data['last_message'])
                        await message.delete()
                    except: pass
                try:
                    if is_embed:
                        embed = Embed(color=self.bot.config.DEFAULT_EMBED_COLOR, title=text)
                        if track is not None:
                            embed.add_field(name=await self.bot.get_locale(guild_id, 'DURATION'), value=format_millis_to_time(track.length))
                            if put_by is not None: embed.add_field(name=await self.bot.get_locale(guild_id, 'PUT_BY'), value=f'<@{put_by}>')
                            if track.artwork_url is not None: embed.set_thumbnail(url=track.artwork_url)
                        message = await channel.send(embed=embed)
                    else: message = await channel.send(text)
                    if replace:
                        await self.bot.config.DB.queue.update_one({'id': guild.id}, {'$set': {'last_message': message.id}})
                except: pass

        if data['loop'] == 'song':
            await send_message((await self.bot.get_locale(guild.id, 'PUT_BY')).format(event.track.title, self.bot.config.SOURCE_EMOJIS[event.track.source]), guild_id=guild.id, replace=True, is_embed=True, track=event.track)
            await player.play(event.track)
            return

        songs_length = len(data['songs'])
        if songs_length == 0:
            await send_message(await self.bot.get_locale(guild.id, 'QUEUE_EMPTY'), guild_id=guild.id)
            await self.bot.config.DB.queue.delete_one({'id': guild.id})
            return await guild.voice_client.disconnect(force=True)
        
        if data['loop'] == 'queue':
            tryings = 0
            tracks = await player.fetch_tracks(query=data['songs'][data['position_now']+1 if (data['position_now']+1) < len(data['songs']) else 0]['id'], search_type=mafic.SearchType.SOUNDCLOUD if data['songs'][data['position_now']+1 if (data['position_now']+1) < len(data['songs']) else 0]['source'] == 'sc' else mafic.SearchType.YANDEX_MUSIC)
            songs_length-=1
            while (not tracks) and (songs_length > 0):
                tryings+=1
                await self.bot.config.DB.queue.update_one({'id': guild.id}, {'$pull': data['songs'][tryings]})
                await send_message(f"I can`t play song **{decode_text(data['songs'][tryings]['title'])}** {self.bot.config.SOURCE_EMOJIS[data['songs'][tryings]['source']]}. Sorry. Continue by queue (looped).", replace=True, guild_id=guild.id)
                tracks = await player.fetch_tracks(query=data['songs'][tryings]['id'], search_type=mafic.SearchType.SOUNDCLOUD if data['songs'][data['position_now']+1 if (data['position_now']+1) < len(data['songs']) else 0]['source'] == 'sc' else mafic.SearchType.YANDEX_MUSIC)
            
            if not tracks:
                await send_message(await self.bot.get_locale(guild.id, 'QUEUE_EMPTY'), guild_id=guild.id)
                await self.bot.config.DB.queue.delete_one({'id': guild.id})
                return await guild.voice_client.disconnect(force=True)
            
            if (data['position_now']+1) <= len(data['songs']): await self.bot.config.DB.queue.update_one({'id': guild.id}, {'$inc': {'position_now': 1}})
            else: await self.bot.config.DB.queue.update_one({'id': guild.id}, {'$set': {'position_now': 0}})
            await player.play(tracks[0]) # pyright: ignore[reportOptionalSubscript]
            await send_message((await self.bot.get_locale(guild.id, 'QUEUE_EMPTY')).format(tracks[0].title, self.bot.config.SOURCE_EMOJIS[tracks[0].source]), replace=True, guild_id=guild.id, is_embed=True, track=tracks[0], put_by=data['songs'][data['position_now']+1 if (data['position_now']+1) < len(data['songs']) else 0]['put'])
            return
        
        await self.bot.config.DB.queue.update_one({'id': guild.id}, {'$pull': data['songs'][0]})

        tryings = 0
        tracks = await player.fetch_tracks(query=data['songs'][0]['id'], search_type=mafic.SearchType.SOUNDCLOUD if data['songs'][0]['source'] == 'sc' else mafic.SearchType.YANDEX_MUSIC)
        songs_length-=1
        while (not tracks) and (songs_length > 0):
            tryings+=1
            await self.bot.config.DB.queue.update_one({'id': guild.id}, {'$pull': data['songs'][tryings]})
            await send_message(f"I can`t play song **{decode_text(data['songs'][tryings]['title'])}**. Sorry. Continue by queue.", replace=True, guild_id=guild.id)
            tracks = await player.fetch_tracks(query=data['songs'][tryings]['id'], search_type=mafic.SearchType.SOUNDCLOUD if data['songs'][tryings]['source'] == 'sc' else mafic.SearchType.YANDEX_MUSIC)

        if not tracks:
            if channel != None:
                await send_message(await self.bot.get_locale(guild.id, 'QUEUE_EMPTY'), guild_id=guild.id)
                await self.bot.config.DB.queue.delete_one({'id': guild.id})
                return await guild.voice_client.disconnect(force=True)

        await player.play(tracks[0]) # pyright: ignore[reportOptionalSubscript]
        await send_message(f"Continue. Playing {tracks[0].title} {self.bot.config.SOURCE_EMOJIS[tracks[0].source]} now!", replace=True, is_embed=True, track=tracks[0], guild_id=guild.id) # pyright: ignore[reportOptionalSubscript]

    @commands.slash_command(
        name='play',
        description='Search and play any music',
        dm_permission=False
    )
    async def play(self, inter: ApplicationCommandInteraction, query: str) -> None:
        await inter.response.defer()
        if self.bot.available_nodes() == 0: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NODES_DISABLED'))
        if not inter.author.voice: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NEED_TO_BE_IN_VC'))
        if not inter.guild.voice_client:
            try: player = await inter.author.voice.channel.connect(cls=mafic.Player)
            except: return await inter.send(await self.bot.get_locale(inter.guild.id, 'CANT_JOIN_VOICE'), ephemeral=True)
        else: player = inter.guild.voice_client
        if player.channel.id != inter.author.voice.channel.id: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NEED_TO_BE_IN_SAME'), ephemeral=True)
        
        tracks = await player.fetch_tracks(query=query, search_type=mafic.SearchType.SOUNDCLOUD)
        view = View()
        view.add_item(Select(custom_id=f'select_source:{inter.author.id}', placeholder='Select source of track', options=[SelectOption(label='Souncloud', emoji=self.bot.config.SOUNDCLOUD_EMOJI, value='sc'), SelectOption(label='YandexMusic', emoji=self.bot.config.YANDEXMUSIC_EMOJI, value='ym')]))
        if not tracks: return await inter.send("No tracks found. I`m sorry. Let`s try to change source of track?", view=view)

        query_id = generate_random_string(15)
        while await self.bot.config.DB.search_cache.count_documents({'id': query_id}) != 0: query_id = generate_random_string(15)

        async def get_song_id() -> str:
            song_id = generate_random_string(15)
            while await self.bot.config.DB.search_cache.count_documents({'song_id': song_id}) != 0:
                song_id = generate_random_string(15)
            return song_id

        options = []

        if isinstance(tracks, mafic.Playlist):
            for _ in tracks.tracks:
                if len(options) >= 25: continue
                options.append(_)
                options.append([await get_song_id(), _])
        else:
            for _ in tracks:
                if len(options) >= 25: continue
                options.append([await get_song_id(), _])
        
        await self.bot.config.DB.search_cache.insert_many([{'query_id': query_id, 'query_text': code_text(query), 'song_id': _[0], 'song': _[1].uri, 'type': 'sc', 'search_at': round(datetime.now().timestamp())} for _ in options])

        view = View()
        view.add_item(Select(custom_id=f'select_source:{inter.author.id}:{query_id}', placeholder='Select source of track', options=[SelectOption(label='Souncloud', emoji=self.bot.config.SOUNDCLOUD_EMOJI, value='sc', default=True), SelectOption(label='YandexMusic', emoji=self.bot.config.YANDEXMUSIC_EMOJI, value='ym')]))
        view.add_item(Select(custom_id=f'select_song:{inter.author.id}:sc', placeholder='Select any song by this menu', options=[SelectOption(label=_[1].title, value=_[0]) for _ in options]))

        await inter.send(f"I found **{len(options)}** songs for you on **Soundcloud {self.bot.config.SOUNDCLOUD_EMOJI}**", view=view)

    @commands.Cog.listener()
    async def on_dropdown(self, inter: MessageInteraction):
        values = inter.component.custom_id.split(":")
        if len(values) == 1: return
        if values[0] in ['select_source', 'select_song']:
            if int(values[1]) != inter.author.id: return await inter.send("This menu is not for you. Sorry.", ephemeral=True)
            if self.bot.available_nodes() == 0: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NODES_DISABLED'))
            if not inter.author.voice: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NEED_TO_BE_IN_VC'))
            if not inter.guild.voice_client:
                try: player = await inter.author.voice.channel.connect(cls=mafic.Player)
                except: return await inter.send(await self.bot.get_locale(inter.guild.id, 'CANT_JOIN_VOICE'), ephemeral=True)
            else: player = inter.guild.voice_client
            if player.channel.id != inter.author.voice.channel.id: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NEED_TO_BE_IN_SAME'), ephemeral=True)

        if values[0] == 'select_source':
            data = await self.bot.config.DB.search_cache.find_one({'query_id': values[2]})
            if not data:
                print(123)
                await inter.send("I can`t your search in my database. Sorry. You can try again...")
                return await inter.message.delete()
            tracks = await player.fetch_tracks(query=decode_text(data['query_text']), search_type=mafic.SearchType.SOUNDCLOUD if inter.values[0] == 'sc' else mafic.SearchType.YANDEX_MUSIC) # pyright: ignore[reportOptionalSubscript]
            view = View()
            view.add_item(Select(custom_id=f'select_source:{inter.author.id}:{values[2]}', placeholder='Select source of track', options=[SelectOption(label='Souncloud', emoji=self.bot.config.SOUNDCLOUD_EMOJI, value='sc', default = True if inter.values[0] == 'sc' else False), SelectOption(label='YandexMusic', emoji=self.bot.config.YANDEXMUSIC_EMOJI, value='ym', default = True if inter.values[0] == 'ym' else False)])) # pyright: ignore[reportOptionalSubscript]
            if not tracks: return await inter.send("No tracks found. I`m sorry. Let`s try to change source of track?", view=view)

            async def get_song_id() -> str:
                song_id = generate_random_string(15)
                while await self.bot.config.DB.search_cache.count_documents({'song_id': song_id}) != 0:
                    song_id = generate_random_string(15)
                return song_id

            options = []

            if isinstance(tracks, mafic.Playlist):
                for _ in tracks.tracks:
                    if len(options) >= 25: continue
                    options.append(_)
                    options.append([await get_song_id(), _])
            else:
                for _ in tracks:
                    if len(options) >= 25: continue
                    options.append([await get_song_id(), _])
            
            await self.bot.config.DB.search_cache.delete_many({'query_id': values[2]})
            await self.bot.config.DB.search_cache.insert_many([{'query_id': values[2], 'query_text': data['query_text'], 'song_id': _[0], 'song': _[1].uri, 'type': 'sc' if inter.values == 'sc' else 'ym', 'search_at': round(datetime.now().timestamp())} for _ in options])

            view = View()
            view.add_item(Select(custom_id=f'select_source:{inter.author.id}:{values[2]}', placeholder='Select source of track', options=[SelectOption(label='Souncloud', emoji=self.bot.config.SOUNDCLOUD_EMOJI, value='sc', default = True if inter.values[0] == 'sc' else False), SelectOption(label='YandexMusic', emoji=self.bot.config.YANDEXMUSIC_EMOJI, value='ym', default = True if inter.values[0] == 'ym' else False)])) # pyright: ignore[reportOptionalSubscript]
            view.add_item(Select(custom_id=f'select_song:{inter.author.id}:sc', placeholder='Select any song by this menu', options=[SelectOption(label=_[1].title, value=_[0]) for _ in options]))

            await inter.message.edit(content=f"I found **{len(options)}** songs for you on **{'Soundcloud' if inter.values[0] == 'sc' else 'YandexMusic'} {self.bot.config.SOUNDCLOUD_EMOJI if inter.values[0] == 'sc' else self.bot.config.YANDEXMUSIC_EMOJI}**", view=view) # pyright: ignore[reportOptionalSubscript]
            return await inter.response.defer()
        
        if values[0] == 'select_song':
            if round(datetime.now().timestamp())-240 >= round(inter.message.created_at.timestamp()):
                await inter.send("This menu is too old. Sorry.", ephemeral=True)
                return await inter.message.delete()

            data = await self.bot.config.DB.search_cache.find_one({'song_id': inter.values[0]}) # pyright: ignore[reportOptionalSubscript]
            if not data:
                await inter.send("I can`t found any tracks in my database. Sorry. You can try again...", ephemeral=True)
                return await inter.message.delete()
            
            tracks = await player.fetch_tracks(query=data['song'], search_type=mafic.SearchType.SOUNDCLOUD if values[2] == 'sc' else mafic.SearchType.YANDEX_MUSIC)
            if not tracks:
                await self.bot.config.DB.search_cache.delete_many({'query_id': data['query_id']})
                await inter.send("No tracks found. I`m sorry...", ephemeral=True)
                return await inter.message.delete()
            
            track = None
            if isinstance(tracks, mafic.Playlist): track = tracks.tracks[0]
            else: track = tracks[0]
            if not track:
                await self.bot.config.DB.search_cache.delete_many({'query_id': data['query_id']})
                await inter.send("No tracks found. I`m sorry...", ephemeral=True)
                return await inter.message.delete()

            position = 0
            if not player.current:
                await player.play(track)
                if await self.bot.config.DB.queue.count_documents({'id': inter.guild.id}) == 0: await self.bot.config.DB.queue.insert_one({'id': inter.guild.id, 'loop': 0, 'position_now': 0, 'channel': inter.channel.id, 'last_message': 0, 'songs': []})
                else: await self.bot.config.DB.queue.update_one({'id': inter.guild.id}, {'$set': {'songs': [], 'loop': 'n', 'position_now': 0, 'channel_id': inter.channel.id}})
            else:
                position = await self.add_song(inter.guild.id, inter.author, inter.channel, track) # pyright: ignore[reportArgumentType]
            await inter.message.edit(content=(await self.bot.get_locale(inter.guild.id, 'PLAYING_NOW')).format(track.title, self.bot.config.SOURCE_EMOJIS[track.source]) if position == 0 else f'Song **{track.title}** {self.bot.config.SOURCE_EMOJIS[track.source]} added to **{position} position** in queue!', view=None)
            await inter.response.defer()
            await self.bot.config.DB.search_cache.delete_many({'query_id': data['query_id']})
            return await self.bot.config.DB.queue.update_one({'id': inter.guild.id}, {'$set': {'last_message': inter.message.id}})
    
    @commands.slash_command(
        name='loop',
        description='Loop queue or song',
        dm_permission=False
    )
    async def loop(self, inter: ApplicationCommandInteraction, type: str = commands.Param(name='type', choices=['song', 'queue'])):
        await inter.response.defer()
        if self.bot.available_nodes() == 0: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NODES_DISABLED'))
        if not inter.author.voice: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NEED_TO_BE_IN_VC'))
        if not inter.guild.voice_client: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        else: player: mafic.Player = inter.guild.voice_client # pyright: ignore[reportAssignmentType]
        if player.channel.id != inter.author.voice.channel.id: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NEED_TO_BE_IN_SAME'), ephemeral=True)
        if not player.current: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        data = await self.bot.config.DB.queue.find_one({'id': inter.guild.id})
        loop_status = 'n' if not data else data['loop']
        if type == 'song':
            if not data: await self.bot.config.DB.queue.insert_one({'id': inter.guild.id, 'loop': 'song', 'position_now': 0, 'channel': inter.channel.id, 'last_message': 0, 'songs': []})
            else: await self.bot.config.DB.queue.update_one({'id': inter.guild.id}, {'$set': {'loop': 'song' if loop_status in ['n', 'queue'] else 'n'}})
            return await inter.send(f"Song **{player.current.title}** __is looped__ now!" if loop_status in ['n', 'queue'] else f"Song **{player.current.title}** __is not looped__ now!") # pyright: ignore[reportOptionalSubscript]
        if not data: await self.bot.config.DB.queue.insert_one({'id': inter.guild.id, 'loop': 'queue', 'position_now': 0, 'channel': inter.channel.id, 'last_message': 0, 'songs': [{'title': code_text(player.current.title), 'id': player.current.uri, 'put': self.bot.user.id, 'custom_id': generate_random_string(15)}]})
        else:
            if loop_status == 'queue': await self.bot.config.DB.queue.update_one({'id': inter.guild.id}, {'$pull': {'songs': data['songs'][0]}})
            else: await self.bot.config.DB.queue.update_one({'id': inter.guild.id}, {'$push': {'songs': {'$each': [{'title': code_text(player.current.title), 'id': player.current.uri, 'put': self.bot.user.id, 'source': player.current.source, 'custom_id': generate_random_string(15)}], '$position': 0}}})
            await self.bot.config.DB.queue.update_one({'id': inter.guild.id}, {'$set': {'loop': 'queue' if loop_status in ['n', 'song'] else 'n'}})
        return await inter.send(f"Queue __is looped__ now!" if loop_status in ['n', 'song'] else f"Queue __is not looped__ now!") # pyright: ignore[reportOptionalSubscript]
    
    @commands.slash_command(
        name='queue',
        description='Get queue of tracks',
        dm_permission=False
    )
    async def queue(self, inter: ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        if self.bot.available_nodes() == 0: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NODES_DISABLED'))
        if not inter.guild.voice_client: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        if not inter.guild.voice_client: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        else: player: mafic.Player = inter.guild.voice_client # pyright: ignore[reportAssignmentType]
        songs: list[CordySong] = []
        data = await self.bot.config.DB.queue.find_one({'id': inter.guild.id})
        if not data: songs.append(CordySong(1, player.current.title, 'sc' if player.current.source == 'soundcloud' else 'ym', playing_now = True))
        elif len(data['songs']) == 0: songs.append(CordySong(1, player.current.title, 'sc' if player.current.source == 'soundcloud' else 'ym', playing_now = True))
        elif data['loop'] == 'queue':
            position = 1
            for _ in data['songs']:
                songs.append(CordySong(position, decode_text(data['songs'][position-1]['title']), data['songs'][position-1]['source'], playing_now = True if data['position_now']-1 == position else False))
                position += 1
        else:
            songs.append(CordySong(1, player.current.title, 'sc' if player.current.source == 'soundcloud' else 'ym', playing_now = True))
            position = 2
            for _ in data['songs']:
                songs.append(CordySong(position, decode_text(data['songs'][position-2]['title']), 'sc' if data['songs'][position-2]['source'] == 'soundcloud' else 'ym'))
                position += 1
        message = ''
        for _ in songs:
            message += f'**{"(NOW) " if _.playing_now else ""}#{_.position} —** {_.title} {self.bot.config.SOURCE_EMOJIS[_.source]}\n'
        embed = await self.bot.embeds.simple()
        embed.description = message
        if self.bot.user.avatar is not None: embed.set_thumbnail(url=self.bot.user.avatar.url)
        elif player.current.artwork_url is not None: embed.set_thumbnail(url=player.current.artwork_url)
        if data is not None:
            if data['loop'] == 'song': embed.set_footer(text=await self.bot.get_locale(inter.guild.id, 'SONG_LOOPED'))
            elif data['loop'] == 'queue': embed.set_footer(text=await self.bot.get_locale(inter.guild.id, 'QUEUE_LOOPED'))
        await inter.send(embed=embed)

    @commands.slash_command(
        name='skip',
        description='Skip current playing track',
        dm_permission=False
    )
    async def skip(self, inter: ApplicationCommandInteraction):
        if self.bot.available_nodes() == 0: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NODES_DISABLED'))
        if not inter.guild.voice_client: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        if not inter.guild.voice_client: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        else: player: mafic.Player = inter.guild.voice_client # pyright: ignore[reportAssignmentType]
        await inter.send((await self.bot.get_locale(inter.guild.id, 'SONG_SKIPPED')).format(player.current.title))
        return await player.stop()

    @commands.slash_command(
        name='stop',
        description='Stop playing all of tracks',
        dm_permission=False
    )
    async def stop(self, inter: ApplicationCommandInteraction):
        if self.bot.available_nodes() == 0: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NODES_DISABLED'))
        if not inter.guild.voice_client: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        if not inter.guild.voice_client: return await inter.send(await self.bot.get_locale(inter.guild.id, 'NOTHING_PLAYING'), ephemeral=True)
        else: player: mafic.Player = inter.guild.voice_client # pyright: ignore[reportAssignmentType]
        await inter.send(await self.bot.get_locale(inter.guild.id, 'PLAYING_STOPPED'))
        await self.bot.config.DB.queue.delete_one({'id': inter.guild.id})
        return await player.disconnect(force=True)

def setup(bot: Cordy):
    bot.add_cog(MusicCog(bot))