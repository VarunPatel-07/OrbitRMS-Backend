from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ProjectStatus(BaseModel):
    status_name: str
    status_color: str


class Department(BaseModel):
    department_name: str


class Designations(BaseModel):
    designations_name: str


class PermissionModule(BaseModel):
    label: str
    is_allowed: bool
    show_input: bool


class RoleAssociatedPermissionModule(BaseModel):
    module_label: str
    module_title: str
    is_active: bool
    permissions: List[PermissionModule]
    sub_modules: List["RoleAssociatedPermissionModule"] = []


class RolesPermission(BaseModel):
    role_name: str
    description: str
    permission_module: List[RoleAssociatedPermissionModule]


class CloneRole(BaseModel):
    clone_role_name: str
    clone_role_id: str
    config_module_id: str


class AddRolesPermission(BaseModel):
    role_name: str
    description: str
    status: bool
    clone_role_info: Optional[CloneRole]
