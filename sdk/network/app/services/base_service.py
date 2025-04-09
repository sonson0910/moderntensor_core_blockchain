from typing import Any, Protocol

from sdk.network.app.schema.base_schema import APIResponseModel, Blank


class RepositoryProtocol(Protocol):
    def read_by_options(self, schema: Any) -> Any: ...

    def read_by_id(self, id: int) -> Any: ...

    def create(self, schema: Any) -> Any: ...

    def update(self, id: int, schema: Any) -> Any: ...

    def update_attr(self, id: int, attr: str, value: Any) -> Any: ...

    def whole_update(self, id: int, schema: Any) -> Any: ...

    def delete_by_id(self, id: int) -> Any: ...


class BaseService:
    def __init__(self, repository: RepositoryProtocol) -> None:
        self._repository = repository

    def get_list(self, schema: Any) -> Any:
        return APIResponseModel(
            status_code = 209,
            data=schema,
            is_success = True,
            msg_err = "Ok"
        )
        return self._repository.read_by_options(schema)

    def get_by_id(self, id: int) -> Any:
        return APIResponseModel(
            status_code = 200,
            data=id,
            is_success = True,
            msg_err = "Ok"
        )
        return self._repository.read_by_id(id)

    def add(self, schema: Any) -> Any:
        return APIResponseModel(
            status_code = 200,
            data=schema,
            is_success = True,
            msg_err = "add Ok"
        )
        return self._repository.create(schema)

    def patch(self, id: int, schema: Any) -> Any:
        return APIResponseModel(
            status_code = 200,
            data=schema,
            is_success = True,
            msg_err = "update Ok"
        )
        return self._repository.update(id, schema)

    def patch_attr(self, id: int, attr: str, value: Any) -> Any:
        return APIResponseModel(
            status_code = 200,
            data=attr,
            is_success = True,
            msg_err = "Update attr ok"
        )
        return self._repository.update_attr(id, attr, value)

    def put_update(self, id: int, schema: Any) -> Any:
        return self._repository.whole_update(id, schema)

    def remove_by_id(self, id: int) -> Any:
        return Blank()
        return self._repository.delete_by_id(id)

    def close_scoped_session(self):
        self._repository.close_scoped_session()