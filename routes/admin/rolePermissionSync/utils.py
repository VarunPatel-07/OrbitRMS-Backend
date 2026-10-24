import copy
import json
import os

from fastapi import HTTPException, status

from constants.constant import SUCCESS
from models.pydantic.ConfigModule.ConfigModule import RoleAssociatedPermissionModule, RolesPermission

DEFAULT_ROLE_PERMISSION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "jobs",
    "backgroundHandler",
    "data",
    "defaultRolePermissionData.json",
)


def load_default_roles_permission_json() -> dict:
    try:
        with open(DEFAULT_ROLE_PERMISSION_PATH, "r") as file_content:
            data = json.load(file_content)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Default role permission data file not found", "success": SUCCESS.FALSE},
        )
    return {each["role_name"].lower(): RolesPermission(**each) for each in data}


def disable_all_permissions(module: RoleAssociatedPermissionModule) -> RoleAssociatedPermissionModule:
    module = copy.deepcopy(module)

    def walk(node: RoleAssociatedPermissionModule):
        for permission in node.permissions:
            permission.is_allowed = False
        for sub_module in node.sub_modules:
            walk(sub_module)

    walk(module)
    return module


