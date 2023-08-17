from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import timedelta
from time import time

from discord import Member

from core.embed import EmbedField

if TYPE_CHECKING:
    from main import CustomBot
    from core.context import CustomContext


class GenericItem:

    TYPE_MAP = {
        'GenericItem': 'Miscellaneous',
        'AutoRoleItem': 'Auto-Role',
        'GiveawayEntryItem': 'Giveaway'
    }

    def __init__(self, bot: CustomBot, **kwargs):
        self.bot: CustomBot = bot

        self.name: str = kwargs.get('name', 'Item Name')
        self.uiid: str = kwargs.get('uiid', 'Unique Item ID')
        self.desc: str = kwargs.get('desc', 'Item Description')
        self.cost: int = kwargs.get('cost', 0)

        self.data = kwargs

    def _desc(self) -> str:
        return f'*{self.desc}*\n> **Type:** `{self.TYPE_MAP[self.__class__.__name__]}`\n> **Cost:** `{self.cost:,}`'

    def to_embed_field(self) -> EmbedField:
        name = f'{self.name} (Item ID: `{self.uiid}`)'
        text = self._desc()
        return EmbedField(name=name, text=text)

    async def _do_transaction(self, member: Member) -> None:
        member_data: dict = await self.bot.mongo_db.user_tokens_entry(member.id)
        bought_items: list[dict] = member_data.get('bought_items', [])
        balance: int = member_data.get('tokens', 0)

        for bought_item in bought_items:
            if bought_item.get('uiid') == self.uiid:
                raise Exception('You\'ve already bought that item!')
        if balance < self.cost:
            raise Exception('You cannot afford that!')

        await self.bot.mongo_db.edit_user_items(member.id, bought_items + [self.data])
        await self.bot.mongo_db.edit_user_tokens(member.id, -self.cost)

    async def redeem(self, ctx: CustomContext, member: Member) -> None:
        await self._do_transaction(member)

        await self.bot.good_embed(
            ctx,
            f'*Bought item: `{self.name}`! '
            f'Contact a staff member to manually redeem your reward.*'
        )


class AutoRoleItem(GenericItem):

    def __init__(self, bot: CustomBot, **kwargs):
        super().__init__(bot, **kwargs)

        self.role_id: int = kwargs.get('role_id', 0)
        self.duration: int = kwargs.get('duration', 3600)

    def _desc(self) -> str:
        return super()._desc() + f'\n> **Role:** <@&{self.role_id}>\n> **Lasts:** `{timedelta(seconds=self.duration)}`'

    async def redeem(self, ctx: CustomContext, member: Member) -> None:
        role = self.bot.guild.get_role(self.role_id)
        if not role:
            raise Exception('Role not found. Please contact a staff member for support.')
        elif role in member.roles:
            raise Exception('You already have that role.')

        self.data['until'] = time() + self.duration

        await self._do_transaction(member)
        await member.add_roles(role)

        await self.bot.good_embed(
            ctx,
            f'*Bought item: `{self.name}`! '
            f'You now have the {role.mention} role.*'
        )


class GiveawayEntryItem(GenericItem):

    def __init__(self, bot: CustomBot, **kwargs):
        super().__init__(bot, **kwargs)

        self.count: int = kwargs.get('count', 1)

    def _desc(self) -> str:
        return super()._desc() + f'\n> **Bonus Giveaway Entries:** `{self.count}`'

    async def redeem(self, ctx: CustomContext, member: Member) -> None:
        await self._do_transaction(member)

        await self.bot.good_embed(
            ctx,
            f'*Bought item: `{self.name}`! '
            f'Your bonus entries will be automatically applied when you next enter a giveaway.*'
        )


SHOP_ITEM = GenericItem | AutoRoleItem | GiveawayEntryItem


def item_constructor(bot: CustomBot, **kwargs) -> SHOP_ITEM:
    item_type = kwargs.get('type')

    if item_type == 'auto_role':
        cls = AutoRoleItem
    elif item_type == 'bonus_gwe':
        cls = GiveawayEntryItem
    else:
        cls = GenericItem

    return cls(bot, **kwargs)
