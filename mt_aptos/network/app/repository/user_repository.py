from mt_aptos.network.app.model.user import User
from mt_aptos.network.app.repository.base_repository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)
