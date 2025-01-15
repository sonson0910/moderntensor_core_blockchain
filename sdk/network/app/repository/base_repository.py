from typing import Any,  Type, TypeVar

from app.core.config import configs
from app.core.exceptions import DuplicatedError, NotFoundError
from app.model.base_model import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository:
    def __init__(self, model: Type[T]) -> None:
        self.model = model

    def read_by_id(self, id: int, eager: bool = False):
        return None

    def create(self, schema: T):
        return None
    
    def update(self, id: int, schema: T):
        return None

    def update_attr(self, id: int, field: str, value: Any):
        return None

    def whole_update(self, id: int, schema: T):
         return None

    def delete_by_id(self, id: int):
         return None

    # def close_scoped_session(self):
    #     with self.session_factory() as session:
    #         return session.close()
