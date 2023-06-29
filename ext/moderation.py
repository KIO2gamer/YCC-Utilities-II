from unicodedata import normalize
from random import randint

from discord.ext import commands
from discord import (
    Member
)

from main import CustomBot
from core.context import CustomContext


class ModerationCommands(commands.Cog):

    _reason = 'No reason provided.'

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.command(
        name='decancer',
        aliases=['dc'],
        description='Converts a member\'s nickname into standard English font.',
        extras={'requirement': 1}
    )
    @commands.bot_has_permissions(manage_nicknames=True)
    async def decancer(self, ctx: CustomContext, *, member: Member):
        await self.bot.check_target_member(member)

        new_nickname = normalize('NFKD', member.display_name).encode('ascii', 'ignore').decode('utf-8')
        await member.edit(nick=new_nickname)

        await self.bot.good_embed(ctx, f'Changed {member.mention}\'s nickname.')

    @commands.command(
        name='modnick',
        aliases=['mn'],
        description='Assigns a randomly-generated nickname to a member.',
        extras={'requirement': 1}
    )
    @commands.bot_has_permissions(manage_nicknames=True)
    async def modnick(self, ctx: CustomContext, *, member: Member):
        await self.bot.check_target_member(member)

        new_nickname = f'Moderated Nickname-{hex(randint(1, 10000000))}'
        await member.edit(nick=new_nickname)

        await self.bot.good_embed(ctx, f'Changed {member.mention}\'s nickname.')


async def setup(bot: CustomBot):
    await bot.add_cog(ModerationCommands(bot))
