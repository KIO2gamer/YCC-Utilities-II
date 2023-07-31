import logging

from discord.ext import commands, tasks
from discord import (
    Message,
    Member,
    Embed,
    Color,
    Role
)

from main import CustomBot
from core.embed import EmbedField
from core.context import CustomContext
from components.paginator import Paginator
from api.errors import HTTPException


class TokenHandler(commands.Cog):

    MEE6_EXCEPTION = 'Failed to fetch MEE6 stats for {0}. It is possible that they\'re not ranked yet.'

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.recent_user_ids: list[int] = []

    def cog_load(self) -> None:
        self.update_user_tokens.start()

    def cog_unload(self) -> None:
        self.update_user_tokens.stop()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.id not in self.recent_user_ids and not message.author.bot:
            self.recent_user_ids.append(message.author.id)

    @tasks.loop(minutes=30)
    async def update_user_tokens(self):
        for user_id in self.recent_user_ids:
            self.recent_user_ids.remove(user_id)

            try:
                current_level = await self.bot.mee6.user_level(self.bot.guild_id, user_id)
                known_level = (await self.bot.mongo_db.user_tokens_entry(user_id)).get('known_level')
            except HTTPException:
                logging.error(self.MEE6_EXCEPTION.format(f'<@{user_id}>'))
                break

            for _ in range(current_level - known_level):
                await self.bot.mongo_db.update_user_level(user_id)

    @commands.command(
        name='coins',
        aliases=['tokens'],
        description='Displays the member\'s current Café Coins balance as well as their known MEE6 level.',
        extras={'requirement': 0}
    )
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def coins(self, ctx: CustomContext, member: Member = None):
        async with ctx.typing():
            member = member or ctx.author
            if member.bot:
                raise Exception(f'{member.mention} is a bot.')
            try:
                data = await self.bot.mongo_db.user_tokens_entry(member.id)
            except HTTPException:
                raise Exception(self.MEE6_EXCEPTION.format(member.mention))

            tokens_embed = Embed(color=Color.blue(), description=member.mention)

            tokens_embed.set_author(name='Café Coins', icon_url=self.bot.user.avatar or self.bot.user.default_avatar)
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
        description='Edits the Café Coins balance of a member. Balances cannot go below zero.',
        extras={'requirement': 4}
    )
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def editcoins(self, ctx: CustomContext, member: Member, coin_change: int):
        async with ctx.typing():
            if member.bot:
                raise Exception(f'{member.mention} is a bot.')
            try:
                result = await self.bot.mongo_db.edit_user_tokens(member.id, coin_change)
            except HTTPException:
                raise Exception(self.MEE6_EXCEPTION.format(member.mention))

            new_balance = result.get('tokens')

        await self.bot.good_embed(ctx, f'*Edited {member.mention}\'s balance to `{new_balance:,}` coins.*')

    @commands.command(
        name='addtokenrole',
        aliases=[],
        description='Members with the specified role will receive bonus Café Coins once per week.',
        extras={'requirement': 4}
    )
    async def addtokenrole(self, ctx: CustomContext, role: Role, coin_bonus: int):
        await self.bot.mongo_db.add_bonus_token_roles(role_id=role.id, bonus=coin_bonus)
        await self.bot.good_embed(ctx, f'*{role.mention} will now reward `{coin_bonus:,}` bonus Café coins per week.*')

    @commands.command(
        name='deltokenrole',
        aliases=[],
        description='Deletes a weekly bonus Café Coin role assignment.',
        extras={'requirement': 4}
    )
    async def deltokenrole(self, ctx: CustomContext, role: Role):
        result = await self.bot.mongo_db.del_bonus_token_roles(role_id=role.id)
        if result is False:
            raise Exception(f'{role.mention} is not a bonus Café Coin role.')
        await self.bot.good_embed(ctx, f'*Unassigned {role.mention} as a bonus Café Coin role.*')

    @commands.command(
        name='tokenroles',
        aliases=[],
        description='Lists all bonus Café Coin role assignments.',
        extras={'requirement': 1}
    )
    async def tokenroles(self, ctx: CustomContext):
        bonus_token_roles = await self.bot.mongo_db.get_bonus_token_roles()
        if not bonus_token_roles:
            raise Exception(f'No roles found. Use `{self.bot.command_prefix}addtokenrole` to create one!')

        fields = [EmbedField(
            name='Bonus Role',
            text=f'> **Role:** <@&{entry.get("role_id", 0)}>\n> **Bonus: `{entry.get("bonus", 0):,}`**')
            for entry in bonus_token_roles]
        embeds = self.bot.fields_to_embeds(fields, title='Bonus Café Coin Roles')

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))


async def setup(bot: CustomBot):
    await bot.add_cog(TokenHandler(bot))
