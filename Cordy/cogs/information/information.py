from disnake import ApplicationCommandInteraction, Embed
from disnake.ext import commands

from core.bot import Cordy

class InformationCog(commands.Cog):
    def __init__(self, bot: Cordy) -> None:
        self.bot = bot
        
    @commands.slash_command(
        name = 'help',
        description = 'List of bot commands',
        dm_permission=False
    )
    async def help(
        self, 
        inter: ApplicationCommandInteraction,
    ):
        await inter.response.defer()
        embed: Embed = await inter.bot.embeds.simple()
        embed.title = await self.bot.get_locale(inter.guild.id, 'HELP_TITLE')
        embed.description = (await self.bot.get_locale(inter.guild.id, 'HELP_DESC')).format(
            inter.bot.get_global_command_named('help'), inter.bot.get_global_command_named('bot'),
            inter.bot.get_global_command_named('play'), inter.bot.get_global_command_named('skip'),
            inter.bot.get_global_command_named('stop'), inter.bot.get_global_command_named('loop'), inter.bot.get_global_command_named('queue')
        )
        embed.set_thumbnail(url=inter.bot.user.avatar.url)
        await inter.send(embed=embed)

    @commands.slash_command(
        name = 'bot',
        description ='Get information about the bot',
        dm_permission=False
    )
    async def _bot(
        self, 
        inter: ApplicationCommandInteraction,
    ):
        await inter.response.defer()
        embed: Embed = await inter.bot.embeds.simple()
        embed.description = f'''
        '''
        if self.bot.available_nodes == 0: embed.description += f'\n{await self.bot.get_locale(inter.guild.id, "NODES_DISABLED")}'
        else:
            for node in self.bot.pool.nodes:
                stats = node.stats
                embed.add_field(name=f'Music node #{node.label}', value=f'Players: {stats.playing_player_count}/{stats.player_count}')
        await inter.send(embed=embed)

def setup(bot: Cordy):
    bot.add_cog(InformationCog(bot))