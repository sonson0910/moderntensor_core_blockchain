from typing import List
from fastapi import UploadFile
from mt_core.network.app.repository.user_repository import UserRepository
from mt_core.network.app.schema.base_schema import APIResponseModel
from mt_core.network.app.services.base_service import BaseService


class UserService(BaseService):
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        super().__init__(user_repository)

    def add_file(self, files: List[UploadFile]):
        for file in files:
            if not (file.filename.endswith('.json') or file.filename.endswith('.txt')):
                return APIResponseModel(
                    status_code = 500,
                    data="file not ok",
                    is_success = False,
                    msg_err = "Each file must be a .json or .txt file"
                )
        return APIResponseModel(
            status_code = 200,
            data="file ok",
            is_success = True,
            msg_err = "upload Ok"
        )

