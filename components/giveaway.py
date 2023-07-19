from asyncio import sleep
from random import sample

from discord import ui
from discord import (
    ButtonStyle,
    HTTPException,
    Interaction,
    Message,
    User
)


# noinspection PyUnusedLocal,PyUnresolvedReferences
class GiveawayView(ui.View):

    def __init__(self, message: Message, winners: int, duration: int, prize: str):
        super().__init__(timeout=None)

        self.message, self.winners, self.duration, self.prize = message, winners, duration, prize
        self.entries: list[User] = []

    @ui.button(label='Enter Giveaway', style=ButtonStyle.green, emoji='🎉')
    async def enter(self, interaction: Interaction, button):
        if interaction.user in self.entries:
            return await interaction.response.send_message('**You\'ve already entered this giveaway.**', ephemeral=True)
        self.entries.append(interaction.user)
        await interaction.response.send_message('**Giveaway entered!**', ephemeral=True)

    async def _send_winners(self, winners: list[User]):
        if winners:
            winner_str = f'**Congrats {", ".join([u.mention for u in winners])}, you won a giveaway: `{self.prize}`!**'
        else:
            winner_str = f'**No one entered the giveaway!**'
        try:
            await self.message.reply(winner_str)
        except HTTPException:
            await self.message.channel.send(winner_str)

    async def expire(self):
        await sleep(self.duration)

        self.stop()
        self.enter.disabled = True

        try:
            winners = sample(self.entries, self.winners)
        except ValueError:
            winners = self.entries

        try:
            await self.message.edit(view=self)
            await self._send_winners(winners)
        except HTTPException:
            pass
