from typing import List
from dependency_injector.wiring import Provide
from fastapi import APIRouter, Depends, File, UploadFile

from mt_aptos.network.app.core.container import Container
from mt_aptos.network.app.core.middleware import inject
from mt_aptos.network.app.schema.base_schema import APIResponseModel, Blank
from mt_aptos.network.app.schema.user_schema import (
    FindUser,
    FindUserResult,
    UploadUserFile,
    UpsertUser,
    User,
)
from mt_aptos.network.app.services.user_service import UserService

router = APIRouter(prefix="/user", tags=["user"])

# Dependency injection


@router.get("", response_model=FindUserResult)
@inject
def get_user_list(
    find_query: FindUser = Depends(),
    service: UserService = Depends(Provide[Container.user_service]),
):
    return service.get_list(find_query)


@router.get("/{user_id}", response_model=APIResponseModel)
@inject
def get_user(
    user_id: int, service: UserService = Depends(Provide[Container.user_service])
):
    return service.get_by_id(user_id)


@router.post("", response_model=APIResponseModel)
@inject
def create_user(
    user: UpsertUser, service: UserService = Depends(Provide[Container.user_service])
):
    return service.add(user)


@router.post("/files", response_model=APIResponseModel)
@inject
def create_user_file(
    files: List[UploadFile] = File(..., description=".txt | .json"),
    service: UserService = Depends(Provide[Container.user_service]),
):
    return service.add_file(files)


@router.patch("/{user_id}", response_model=APIResponseModel)
@inject
def update_user(
    user_id: int,
    user: UpsertUser,
    service: UserService = Depends(Provide[Container.user_service]),
):
    return service.patch(user_id, user)


@router.delete("/{user_id}", response_model=Blank)
@inject
def delete_user(
    user_id: int, service: UserService = Depends(Provide[Container.user_service])
):
    return service.remove_by_id(user_id)
