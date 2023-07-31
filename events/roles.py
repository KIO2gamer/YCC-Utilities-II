import logging

from discord.ext import commands
from discord import (
    HTTPException,
    Member,
    Role
)

from main import CustomBot


class SpecialRoleEvents(commands.Cog):

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.Cog.listener(name='on_guild_role_delete')
    async def handle_deleted_roles(self, role: Role):
        custom_roles = await self.bot.mongo_db.fetch_roles('custom')
        persistent_roles = await self.bot.mongo_db.fetch_roles('persistent')
        bonus_token_roles = await self.bot.mongo_db.get_bonus_token_roles()

        for custom_role in custom_roles:
            role_id = custom_role.get('role_id')
            if role.id == role_id:
                await self.bot.mongo_db.delete_role('custom', role_id=role_id)
        for persistent_role in persistent_roles:
            role_id = persistent_role.get('role_id')
            if role.id == role_id:
                await self.bot.mongo_db.delete_role('persistent', role_id=role_id)
        for bonus_token_role in bonus_token_roles:
            role_id = bonus_token_role.get('role_id')
            if role.id == role_id:
                await self.bot.mongo_db.del_bonus_token_roles(role_id=role_id)

    @commands.Cog.listener(name='on_member_join')
    async def add_persistent_roles(self, member: Member):
        for persistent_role in await self.bot.mongo_db.fetch_roles('persistent'):
            user_id = persistent_role.get('user_id')
            role_id = persistent_role.get('role_id')
            if member.id == user_id:
                try:
                    role = self.bot.guild.get_role(role_id)
                    await member.add_roles(role)
                except (HTTPException, AttributeError) as error:
                    logging.error(f'Could\'t add persistent role (ID: {role_id}) to member (ID: {user_id}) - {error}')


async def setup(bot: CustomBot):
    await bot.add_cog(SpecialRoleEvents(bot))
