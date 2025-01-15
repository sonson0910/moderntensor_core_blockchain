from enum import Enum
from typing import List, Optional

from fastapi import File, UploadFile
from pydantic import BaseModel, Field, field_validator

from app.schema.base_schema import FindBase, ModelBaseInfo, SearchOptions
from app.util.schema import AllOptional

class UserRole(Enum):
    SUBNET = 0
    VALIDATOR = 1
    MINER = 2
    ROOT = 3


class BaseUser(BaseModel):
    net_uid: int
    addr: str = Field(..., description="Wallet address")
    hot_key: str = Field(..., description="Hot key registation")
    reg_key: str = Field(..., description="Registration key for user")
    role: UserRole = Field(..., description="subnet | validator | miner | root")
    reg_name: Optional[str] = None

    @field_validator('net_uid')
    def check_net_uid(cls, v):
        if v <= 0:
            raise ValueError('net_uid must be a positive integer')
        return v

    @field_validator('addr')
    def check_addr(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Address must not be empty')
        if not v.startswith("addr"):
            raise ValueError('Address must start with "addr"')
        return v

    @field_validator('hot_key', 'reg_key')
    def check_keys(cls, v):
        if len(v) < 5:
            raise ValueError('Keys must be at least 5 characters long')
        return v


class User(ModelBaseInfo, BaseUser, metaclass=AllOptional): ...

class FindUser(FindBase, BaseUser, metaclass=AllOptional): ...

class UpsertUser(BaseUser, metaclass=AllOptional): ...

# source: https://stackoverflow.com/questions/65504438/how-to-add-both-file-and-json-body-in-a-fastapi-post-request/70640522#70640522
class UploadUserFile(BaseModel):
    files: List[UploadFile] = File(...,description="file must by .json | .txt")
    
    @field_validator('files')
    def check_file_format(cls, v):
        for file in v:
            if not (file.filename.endswith('.json') or file.filename.endswith('.txt')):
                raise ValueError('Each file must be a .json or .txt file')
        return v

class FindUserResult(BaseModel):
    founds: Optional[List[User]]
    search_options: Optional[SearchOptions]
