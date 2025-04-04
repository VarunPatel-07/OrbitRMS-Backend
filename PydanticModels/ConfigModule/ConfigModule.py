from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import List


class ProjectStatus(BaseModel):
    status_name: str
    status_color: str


class AttachmentType(BaseModel):
    attachment_name: str


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
    sub_modules: List['RoleAssociatedPermissionModule'] = []


class RolesPermission(BaseModel):
    role_name: str
    description: str
    permission_module: List[RoleAssociatedPermissionModule]
