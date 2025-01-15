from app.model.user import User
from app.repository.base_repository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)
