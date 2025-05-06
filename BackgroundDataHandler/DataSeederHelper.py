from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func

from PydanticModels.ConfigModule.ConfigModule import (
    Department,
    Designations,
    ProjectStatus,
    RoleAssociatedPermissionModule,
    RolesPermission,
)
from SqlModels import Models


# This is The Recursive Function That Helps to Add The Data Recursively In To The DataBase
def recursive_creation_helper(
    module_data: RoleAssociatedPermissionModule,
    db,
    role_module_id,
    parent_module_id: Optional[str] = None,
):

    parent_module = Models.RoleAssociatedPermissionModule(
        module_label=module_data.module_label,
        module_title=module_data.module_title,
        is_active=module_data.is_active,
        parent_module_id=parent_module_id,
        role_module_id=role_module_id,
    )

    db.add(parent_module)
    db.flush()

    for permission in module_data.permissions:
        permission_module = Models.PermissionModule(
            label=permission.label,
            is_allowed=permission.is_allowed,
            show_input=permission.show_input,
            associated_permissions_module_id=parent_module.id,
        )
        db.add(permission_module)

    for submodule in module_data.sub_modules:
        recursive_creation_helper(
            submodule, db, role_module_id, parent_module.id  # Set parent ID for submodules
        )

    return parent_module


# This Function Will Allow To Handel The Adding The Data In To The Database


def roles_permission_data_seeder_helper(db, organization_id: str, data: RolesPermission):

    config_module = (
        db.query(Models.ConfigModule)
        .filter(Models.ConfigModule.organization_id == organization_id)
        .first()
    )
    if not config_module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Config Module Not Found", "success": False},
        )

    existing_config_role_module = (
        db.query(Models.ConfigRoleModule)
        .filter(func.lower(Models.ConfigRoleModule.role_name) == func.lower(data.role_name))
        .first()
    )

    if existing_config_role_module:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Role Module With This Name Is Already Exist",
                "success": False,
            },
        )

    config_role_module = Models.ConfigRoleModule(
        role_name=data.role_name,
        description=data.description,
        source_type="default",
        config_module_id=config_module.id,
    )

    db.add(config_role_module)
    db.flush()

    for module in data.permission_module:
        permission_module = recursive_creation_helper(
            module, db, role_module_id=config_role_module.id
        )

        config_role_module.associated_permissions.append(permission_module)

    db.commit()
    db.refresh(config_role_module)
    return


def designation_data_seeder_helper_function(db, organization_id: str, data: Designations):

    config_module = (
        db.query(Models.ConfigModule)
        .filter(Models.ConfigModule.organization_id == organization_id)
        .first()
    )

    if not config_module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Config Module Not Found", "success": False},
        )

    existing_designation = (
        db.query(Models.Designations)
        .filter(
            func.lower(Models.Designations.designations_name) == func.lower(data.designations_name)
        )
        .first()
    )

    if existing_designation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Designations Is Already Exist",
                "success": False,
            },
        )

    designations = Models.Designations(
        designations_name=data.designations_name,
        source_type="default",
        config_module_id=config_module.id,
        created_by=None,
        updated_by=None,
    )

    db.add(designations)
    db.commit()
    db.refresh(designations)


def project_status_data_seeder_helper_function(db, organization_id: str, data: ProjectStatus):

    config_module = (
        db.query(Models.ConfigModule)
        .filter(Models.ConfigModule.organization_id == organization_id)
        .first()
    )

    if not config_module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Config Module Not Found", "success": False},
        )

    existing_status = (
        db.query(Models.ProjectStatus)
        .filter(func.lower(Models.ProjectStatus.status_name) == func.lower(data.status_name))
        .first()
    )

    if existing_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Project Status With This Name Is Already Exist",
                "success": False,
            },
        )

    project_status = Models.ProjectStatus(
        status_name=data.status_name,
        status_color=data.status_color,
        source_type="default",
        config_module_id=config_module.id,
        created_by=None,
        updated_by=None,
    )

    db.add(project_status)
    db.commit()
    db.refresh(project_status)


def department_data_seeder_helper_function(db, organization_id: str, data: Department):

    config_module = (
        db.query(Models.ConfigModule)
        .filter(Models.ConfigModule.organization_id == organization_id)
        .first()
    )

    if not config_module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Config Module Not Found", "success": False},
        )

    existing_department = (
        db.query(Models.Department)
        .filter(func.lower(Models.Department.department_name) == func.lower(data.department_name))
        .first()
    )

    if existing_department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "department With This Name Is Already Exist",
                "success": False,
            },
        )

    department = Models.Department(
        department_name=data.department_name,
        source_type="default",
        config_module_id=config_module.id,
        created_by=None,
        updated_by=None,
    )

    db.add(department)
    db.commit()
    db.refresh(department)
