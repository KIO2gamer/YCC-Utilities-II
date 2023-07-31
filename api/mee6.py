from time import time

from api.generic import AsyncRequestsClient
from api.errors import RESPONSE_DATA


class MEE6LevelsAPIClient(AsyncRequestsClient):

    def __init__(self, cache_duration: int | float = 21600, page_user_limit: int = 1000):
        super().__init__()

        self.cache_duration = cache_duration
        self.page_user_limit = page_user_limit

        self._url: str = 'https://mee6.xyz/api/plugins/levels/leaderboard/{0}'
        self._refresh_cache()

    def _refresh_cache(self) -> None:
        self._cache: dict[int, dict[str, dict]] = {}
        self._cache_refresh_time: float = time() + self.cache_duration

    def _guild_data(self, guild_id: int) -> dict[str, dict]:
        data = self._cache.get(guild_id)
        if data is None:
            data = self._cache[guild_id] = {'pages': {}, 'users': {}}
        return data

    async def request(self, method: str, url: str, **kwargs) -> RESPONSE_DATA:
        if self._cache_refresh_time < time():
            self._refresh_cache()
        return await super().request(method, url, **kwargs)

    async def leaderboard_page(self, guild_id: int, page: int = 0) -> list:
        guild_data = self._guild_data(guild_id)
        page_data = guild_data['pages'].get(page)

        if page_data is None:
            params = {'page': page, 'limit': self.page_user_limit}
            response = await self.request('get', self._url.format(guild_id), params=params)
            page_data = guild_data['pages'][page] = response.get('players', [])

        return page_data

    async def user_data(self, guild_id: int, user_id: int) -> dict:
        guild_data = self._guild_data(guild_id)
        user_data = guild_data['users'].get(user_id)

        if user_data is None:

            page_count = 0
            while True:

                page_data = await self.leaderboard_page(guild_id, page_count)
                user_data = next((user for user in page_data if user.get('id') == str(user_id)), None)

                if user_data is not None:
                    guild_data['users'][user_id] = user_data
                    break

                page_count += 1

        return user_data

    async def user_level(self, guild_id: int, user_id: int) -> int:
        user_data = await self.user_data(guild_id, user_id)
        return user_data.get('level', 0)

    async def user_xp_details(self, guild_id: int, user_id: int) -> dict[str, int]:
        user_data = await self.user_data(guild_id, user_id)
        xp_data = user_data.get('detailed_xp', [0, 0, 0])
        return {
            'user_total_xp': xp_data[2],
            'user_level_xp': xp_data[0],
            'total_level_xp': xp_data[1],
            'xp_to_next_level': xp_data[1] - xp_data[0],
        }
