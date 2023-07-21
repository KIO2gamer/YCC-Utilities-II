from discord.ext import commands, tasks
from discord import (
    Message,
    Member,
    Embed,
    Color
)

from main import CustomBot

from core.context import CustomContext
from api.errors import HTTPException


class TokenHandler(commands.Cog):

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.recent_user_ids: list[int] = []

    def cog_load(self) -> None:
        self.update_user_tokens.start()

    def cog_unload(self) -> None:
        self.update_user_tokens.stop()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.id not in self.recent_user_ids:
            self.recent_user_ids.append(message.author.id)

    @tasks.loop(minutes=15)
    async def update_user_tokens(self):
        for user_id in self.recent_user_ids:
            try:
                current_level = await self.bot.mee6.user_level(self.bot.guild_id, user_id)
            except HTTPException:
                break
            if current_level != (await self.bot.mongo_db.user_tokens_entry(user_id)).get('known_level'):
                await self.bot.mongo_db.update_user_level(user_id)
            self.recent_user_ids.remove(user_id)

    @commands.command(
        name='coins',
        aliases=['tokens'],
        description='Displays the member\'s current YT coins count as well as their known MEE6 level.',
        extras={'requirement': 0}
    )
    async def tokens(self, ctx: CustomContext, member: Member = None):
        async with ctx.typing():
            member = member or ctx.author
            data = await self.bot.mongo_db.user_tokens_entry(member.id)

            tokens_embed = Embed(color=Color.blue(), description=member.mention)

            tokens_embed.set_author(name='YouTube Coins', icon_url=self.bot.user.avatar or self.bot.user.default_avatar)
            tokens_embed.set_thumbnail(url=member.avatar or member.default_avatar)
            tokens_embed.set_footer(text='Earn more coins by levelling up!')

            tokens_embed.add_field(
                name='Total Coins:',
                value=f'> :coin: **`{data.get("tokens", 0):,}`**',
                inline=False)
            tokens_embed.add_field(
                name='MEE6 Level:',
                value=f'> <:chat_box:862204558780137482> **`{data.get("known_level", 0):,}`**',
                inline=False)

        await ctx.send(embed=tokens_embed)

    @commands.command(
        name='editcoins',
        aliases=[],
        description='Edits the coin balance of a member. Balance cannot go below zero.',
        extras={'requirement': 3}
    )
    async def editcoins(self, ctx: CustomContext, member: Member, token_delta: int):
        result = await self.bot.mongo_db.edit_user_tokens(member.id, token_delta)
        new_balance = result.get('tokens')
        await self.bot.good_embed(ctx, f'*Edited {member.mention}\'s balance to `{new_balance:,}` coins.*')


async def setup(bot: CustomBot):
    await bot.add_cog(TokenHandler(bot))
