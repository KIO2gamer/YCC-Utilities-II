from weakref import ref

from discord.utils import utcnow


class ModLogEntry:

    def __init__(self, bot, **kwargs):
        self._bot = ref(bot)

        self.raw = kwargs

        self.id: int = kwargs.get('case_id', 0)
        self.mod_id: int = kwargs.get('mod_id', 0)
        self.user_id: int = kwargs.get('user_id', 0)
        self.channel_id: int = kwargs.get('channel_id', 0)

        self.type: str = kwargs.get('type', 'Unknown')
        self.reason: str = kwargs.get('reason', 'No reason provided.')

        self.created: int = kwargs.get('created', 0)
        self.duration: int = kwargs.get('duration', 0)

        self.received: bool = kwargs.get('received', False)
        self.active: bool = kwargs.get('active', False)
        self.deleted: bool = kwargs.get('deleted', False)

    @property
    def bot(self):
        return self._bot()

    @property
    def until(self) -> int:
        return round(self.created + self.duration)

    @property
    def expired(self) -> bool:
        return self.until < utcnow().timestamp()
