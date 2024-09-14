from discord import (
    ui,
    Message,
    Interaction,
    HTTPException
)


class TracebackView(ui.View):

    def __init__(self, bot, message: Message, traceback: str):
        super().__init__(timeout=86400)
        self.bot = bot
        self.message = message
        self.traceback = traceback

    @ui.button(label='Full Traceback')
    async def view_traceback(self, interaction: Interaction, _):
        # noinspection PyUnresolvedReferences
        await interaction.response.send_message(self.traceback, ephemeral=True)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if await self.bot.member_clearance(interaction.user) < 9:
            # noinspection PyUnresolvedReferences
            await interaction.response.send_message('You can\'t use that.', ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            await self.message.edit(view=None)
        except HTTPException:
            pass
