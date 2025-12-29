import json
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from database.CacheDatabase import cache_database
from database.Database import db_dependencies
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from middleware.verifyToken import verify_token
from models.pydantic.ConfigModule.ConfigModule import (
    AddRolesPermission,
    ClientFormSchemaModel,
    Department,
    Designations,
    InquiryFormSchemaSchemaModel,
    ProjectStatus,
    RoleAssociatedPermissionModule,
)
from models.sql import Models
from RateLimiting import limiter
from utils.helper.helper import model_to_filtered_dict

load_dotenv(override=True)


API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING
ROLES_MODULE_API_RATE_LIMITING = "50/minute"

configRoute = APIRouter(prefix="/app/v1/config", tags=["config"])


#  ----- All The Crud Api For The Project Status Start From Here -----


# ?  (1)  API To Add/Edit " Project Status "


@configRoute.post(path="/project_status/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def project_status_function(
    request: Request,
    db: db_dependencies,
    data: ProjectStatus,
    type: str = Query(..., description="Operation type: add or edit"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )
        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

        cache_data_key = f"organization_project_status_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
        )

        updated_created_by_user = model_to_filtered_dict(
            personal_info, ["user_id", "first_name", "last_name"]
        )

        query = db.query(Models.ProjectStatus).filter(
            func.lower(Models.ProjectStatus.status_name) == func.lower(data.status_name),
        )

        if type == "edit" and id:
            query = query.filter(Models.ProjectStatus.id != id)

        if query.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Project Status With This Name Is Already Exist",
                    "success": False,
                },
            )

        if type == "add":

            config_module = (
                db.query(Models.ConfigModule)
                .filter(Models.ConfigModule.organization_id == user.organization_id)
                .first()
            )

            if not config_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Config Module Not Found",
                        "success": False,
                    },
                )

            project_status = Models.ProjectStatus(
                status_name=data.status_name,
                source_type="user_created",
                status_color=data.status_color,
                config_module_id=config_module.id,
                created_by=json.dumps(updated_created_by_user),
                updated_by=None,
            )

            db.add(project_status)
            db.commit()

            return {"success": True, "message": "Project Status Added Successfully"}
        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            project_status = (
                db.query(Models.ProjectStatus).filter(Models.ProjectStatus.id == id).first()
            )

            if not project_status:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Project Status Not Found",
                        "success": False,
                    },
                )

            project_status.status_name = data.status_name
            project_status.updated_by = json.dumps(updated_created_by_user)
            project_status.status_color = data.status_color

            db.commit()

            return {"success": True, "message": "Project Status Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


# ?  (2)  API To Fetch " Project Status "


@configRoute.get(path="/project_status/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_project_status(
    request: Request,
    db: db_dependencies,
    order: str = Query("asc", alias="order"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

        cache_data_key = f"organization_project_status_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)
            cached_sorted_data = sorted(
                cached_Data,
                key=lambda x: datetime.fromisoformat(x["created_at"]),
                reverse=True if order.lower() == "desc" else False,
            )
            return {
                "message": "Project Status Fetched Successfully. Cached!",
                "success": True,
                "data": cached_sorted_data,
            }

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )

        sort_order = order.lower()

        sort_func = asc if sort_order == "asc" else desc

        project_status = (
            db.query(Models.ProjectStatus)
            .filter(Models.ProjectStatus.config_module_id == config_module.id)
            .order_by(sort_func(Models.ProjectStatus.created_at))
        )

        data = [
            model_to_filtered_dict(each_project_status) for each_project_status in project_status
        ]

        await cache_database.set(cache_data_key, json.dumps(jsonable_encoder(data)), ex=3600)

        return {
            "success": True,
            "message": "Project Status Fetched Successfully",
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


# ?  (3)  API To delete " Project Status "


@configRoute.delete(path="/project_status/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def delete_project_status(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="ID for delete operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

        cache_data_key = f"organization_project_status_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        project_status = (
            db.query(Models.ProjectStatus).filter(Models.ProjectStatus.id == id).first()
        )
        if not project_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Project Status Not Found", "success": False},
            )
        db.delete(project_status)
        db.commit()

        return {"message": "Project Status Deleted Successfully", "success": True}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Delete Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


#  ----- All The Crud Api For The Project Status End Here -----


# *  ----- All The Crud Api For The Department Start From Here -----

# ?  (4)  API To Add/Edit " Department "


@configRoute.post(path="/department/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def add_edit_department(
    request: Request,
    db: db_dependencies,
    data: Department,
    type: str = Query(..., description="Operation type: add or edit"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )
        cache_data_key = f"organization_department_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
        )

        query = db.query(Models.Department).filter(
            func.lower(Models.Department.department_name) == func.lower(data.department_name)
        )
        if type == "edit" and id:
            query = query.filter(
                Models.Department.id != id,
            )

        if query.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "department With This Name Is Already Exist",
                    "success": False,
                },
            )

        updated_created_by_user = model_to_filtered_dict(
            personal_info, ["user_id", "first_name", "last_name"]
        )

        if type == "add":

            config_module = (
                db.query(Models.ConfigModule)
                .filter(Models.ConfigModule.organization_id == user.organization_id)
                .first()
            )

            if not config_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Config Module Not Found",
                        "success": False,
                    },
                )

            department = Models.Department(
                department_name=data.department_name,
                config_module_id=config_module.id,
                source_type="user_created",
                created_by=json.dumps(updated_created_by_user),
                updated_by=None,
            )

            db.add(department)
            db.commit()

            return {"success": True, "message": "Department Created Successfully"}
        else:

            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            department = db.query(Models.Department).filter(Models.Department.id == id).first()

            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "No Such department Found", "success": False},
                )

            department.department_name = data.department_name
            department.updated_by = json.dumps(updated_created_by_user)

            db.commit()

            return {"success": True, "message": "department Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add department Right Now",
                "success": False,
                "error": str(e),
            },
        )


# ?  (5)  API To Fetch " department"


@configRoute.get(path="/department/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_department_type(
    request: Request,
    db: db_dependencies,
    order: str = Query("asc", alias="order"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_department_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)
            cached_sorted_data = sorted(
                cached_Data,
                key=lambda x: datetime.fromisoformat(x["created_at"]),
                reverse=True if order.lower() == "desc" else False,
            )
            return {
                "message": "Department Fetched Successfully. Cached!",
                "success": True,
                "data": cached_sorted_data,
            }

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )

        sort_order = order.lower()

        sort_func = asc if sort_order == "asc" else desc

        department = (
            db.query(Models.Department)
            .filter(Models.Department.config_module_id == config_module.id)
            .order_by(sort_func(Models.Department.created_at))
        )

        data = [model_to_filtered_dict(each_department) for each_department in department]

        await cache_database.set(cache_data_key, json.dumps(jsonable_encoder(data)), ex=3600)

        return {
            "success": True,
            "message": "Department Fetched Successfully",
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


# ?  (6)  API To Delete " department "


@configRoute.delete(path="/department/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def delete_department(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="ID for delete operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_department_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        department = db.query(Models.Department).filter(Models.Department.id == id).first()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Department Not Found",
                    "success": False,
                },
            )

        db.delete(department)
        db.commit()

        return {"success": True, "message": "Department Deleted Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Delete Department Right Now",
                "success": False,
                "error": str(e),
            },
        )


# *  ----- All The Crud Api For The department Type End Here -----


#  ----- All The Crud Api For The Designations Start From Here -----


# ?  (7)  API To Add/Edit " Designations "


@configRoute.post(path="/designations/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def add_edit_designations(
    request: Request,
    db: db_dependencies,
    data: Designations,
    type: str = Query(..., description="type Should be 'add' , 'edit'"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )

        cache_data_key = f"organization_designations_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
        )

        query = db.query(Models.Designations).filter(
            func.lower(Models.Designations.designations_name) == func.lower(data.designations_name)
        )

        if type == "edit" and id:
            query = query.filter(Models.Designations.id != id)

        if query.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Designations Is Already Exist",
                    "success": False,
                },
            )

        updated_created_by_user = model_to_filtered_dict(
            personal_info, ["user_id", "first_name", "last_name"]
        )

        if type == "add":

            config_module = (
                db.query(Models.ConfigModule)
                .filter(Models.ConfigModule.organization_id == user.organization_id)
                .first()
            )

            if not config_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Config Module Not Found", "success": False},
                )

            designations = Models.Designations(
                designations_name=data.designations_name,
                source_type="user_created",
                config_module_id=config_module.id,
                created_by=json.dumps(updated_created_by_user),
                updated_by=None,
            )

            db.add(designations)
            db.commit()

            return {"success": True, "message": "Designation Added Successfully"}

        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            designations = (
                db.query(Models.Designations).filter(Models.Designations.id == id).first()
            )

            if not designations:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Designation Not Found", "success": False},
                )

            designations.designations_name = data.designations_name
            designations.updated_by = json.dumps(updated_created_by_user)

            db.commit()

            return {"success": True, "message": "Designation Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add , Edit Designation Right Now",
                "success": False,
                "error": str(e),
            },
        )


# ?  (8)  API To Fetch " Designations "


@configRoute.get(path="/designations/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetch_all_designations(
    request: Request,
    db: db_dependencies,
    order: str = Query("asc", alias="order"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        cache_data_key = f"organization_designations_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:

            cached_Data = json.loads(cached_data)
            cached_sorted_data = sorted(
                cached_Data,
                key=lambda x: datetime.fromisoformat(x["created_at"]),
                reverse=True if order.lower() == "desc" else False,
            )

            return {
                "message": "Designation Fetched Successfully. Cached!",
                "success": True,
                "data": cached_sorted_data,
            }

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )

        sort_order = order.lower()

        sort_func = asc if sort_order == "asc" else desc

        designations = (
            db.query(Models.Designations)
            .filter(Models.Designations.config_module_id == config_module.id)
            .order_by(sort_func(Models.Designations.created_at))
        )

        data = [model_to_filtered_dict(each_designation) for each_designation in designations]

        await cache_database.set(cache_data_key, json.dumps(jsonable_encoder(data)), ex=3600)

        return {
            "message": "Designation Fetched Successfully",
            "success": True,
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Fetch Designation Right Now",
                "success": False,
                "error": str(e),
            },
        )


# ?  (8)  API To Delete " Designations "


@configRoute.delete(path="/designations/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def delete_designation(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="ID for delete operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_designations_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        designations = db.query(Models.Designations).filter(Models.Designations.id == id).first()

        if not designations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Designation Not Found", "success": False},
            )

        db.delete(designations)
        db.commit()

        return {"success": True, "message": "Designation Deleted Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Delete Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


#  ----- All The Crud Api For The Designations End Here -----

# ------- API For The ROles And Permission -----

# todo this api is for testing once it is completed it is moved to background worker


def recursive_creation_helper(
    module_data: RoleAssociatedPermissionModule,
    db,
    role_module_id,
    parent_module_id: Optional[str] = None,
):

    parent_module = Models.RoleAssociatedPermissionModule(
        module_label=module_data.get("module_label"),
        module_title=module_data.get("module_title"),
        is_active=module_data.get("is_active"),
        parent_module_id=parent_module_id,
        role_module_id=role_module_id,
    )

    db.add(parent_module)
    db.flush()

    for permission in module_data.get("permissions"):
        permission_module = Models.PermissionModule(
            label=permission.get("label"),
            is_allowed=permission.get("is_allowed"),
            show_input=permission.get("show_input"),
            associated_permissions_module_id=parent_module.id,
        )
        db.add(permission_module)

    for submodule in module_data.get("sub_modules"):
        recursive_creation_helper(
            submodule, db, role_module_id, parent_module.id  # Set parent ID for submodules
        )

    return parent_module


# ? ------------------------- The Api To Fetch All The Associated Role Of The Organization  -------------------
@configRoute.get("/roles_permissions/fetch-all", status_code=status.HTTP_200_OK)
@limiter.limit(ROLES_MODULE_API_RATE_LIMITING)
async def fetch_all_role_of_organization(
    request: Request,
    db: db_dependencies,
    order: str = Query("asc", alias="order"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):

    try:
        cache_data_key = f"organization_roles_permissions_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)
            cached_sorted_data = sorted(
                cached_Data,
                key=lambda x: datetime.fromisoformat(x["created_at"]),
                reverse=True if order.lower() == "desc" else False,
            )
            return {
                "message": "Roles Fetched Successfully. Cached!",
                "success": True,
                "data": cached_sorted_data,
            }

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )

        sort_order = order.lower()

        sort_func = asc if sort_order == "asc" else desc

        roles_permissions = (
            db.query(Models.ConfigRoleModule)
            .options(joinedload(Models.ConfigRoleModule.associated_employees))
            .filter(Models.ConfigRoleModule.config_module_id == config_module.id)
            .order_by(sort_func(Models.ConfigRoleModule.created_at))
        )

        data = [
            {
                **(model_to_filtered_dict(role_permission)),
                "associated_employees": role_permission.associated_employees,
                "employees": len(role_permission.associated_employees),
            }
            for role_permission in roles_permissions
        ]

        await cache_database.set(cache_data_key, json.dumps(jsonable_encoder(data)), ex=3600)

        return {
            "message": "Roles Fetched Successfully",
            "success": True,
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Fetching All The Role",
                "success": False,
                "error": str(e),
            },
        )


# * ------------------------- This The Comman Function To Build The Hierarchy For The Permission Module  -------------------
def build_hierarchy(modules, parent_id=None):
    filtered_modules = [m for m in modules if m.parent_module_id == parent_id]

    result = []
    for module in filtered_modules:
        if module.parent_module_id == parent_id:
            module_data = {
                "id": module.id,
                "module_label": module.module_label,
                "module_title": module.module_title,
                "is_active": module.is_active,
                "permissions": sorted(
                    [
                        {
                            "id": p.id,
                            "label": p.label,
                            "is_allowed": p.is_allowed,
                            "show_input": p.show_input,
                        }
                        for p in module.permissions
                    ],
                    key=lambda x: x["label"].lower(),
                ),
                "sub_modules": build_hierarchy(modules, module.id),
            }
            result.append(module_data)

    module_with_subs = [module for module in result if module["sub_modules"]]
    module_without_subs = [module for module in result if not module["sub_modules"]]

    module_with_subs.sort(key=lambda x: x["module_title"].lower())
    module_without_subs.sort(key=lambda x: x["module_title"].lower())

    final_result = module_with_subs + module_without_subs

    return final_result


def deactivate_module(module):
    module.is_active = False
    for permission in module.permissions:
        if permission.show_input:
            permission.is_allowed = False

    for sub_module in module.sub_modules:
        deactivate_module(sub_module)


# * ------------------------- The Api To Fetch A Specific Role's Permission  -------------------
@configRoute.get("/roles_permissions/fetch-role", status_code=status.HTTP_200_OK)
@limiter.limit(ROLES_MODULE_API_RATE_LIMITING)
async def fetch_roles_permission(
    request: Request,
    db: db_dependencies,
    role_id: str = Query(..., description="ID of the role to fetch"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_roles_permissions_fetch_role_{role_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)

            return {
                "message": "Role fetched successfully. Cached!",
                "success": True,
                "data": cached_Data,
            }

        # Get all modules for this role (flat structure)
        all_modules = (
            db.query(Models.RoleAssociatedPermissionModule)
            .filter(Models.RoleAssociatedPermissionModule.role_module_id == role_id)
            .options(
                joinedload(Models.RoleAssociatedPermissionModule.permissions),
                joinedload(Models.RoleAssociatedPermissionModule.sub_modules),
            )
            .all()
        )

        if not all_modules:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Role not found",
                    "success": False,
                },
            )

        # Get role details
        role = db.query(Models.ConfigRoleModule).get(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Role not found",
                    "success": False,
                },
            )

        data = {
            "id": role.id,
            "role_name": role.role_name,
            "is_editable": role.is_editable,
            "description": role.description,
            "source_type": role.source_type,
            "status": role.status,
            "created_by": role.created_by,
            "created_at": role.created_at,
            "updated_by": role.updated_by,
            "updated_at": role.updated_at,
            "modules": build_hierarchy(all_modules),
        }

        await cache_database.set(cache_data_key, json.dumps(jsonable_encoder(data)), ex=3600)

        return {
            "message": "Role fetched successfully",
            "success": True,
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Adding The Role And Permission",
                "success": False,
                "error": str(e),
            },
        )


# ? ------------------------- The Api To Update The Roles And Permission  -------------------


@configRoute.put("/roles_permissions/update", status_code=status.HTTP_200_OK)
@limiter.limit(ROLES_MODULE_API_RATE_LIMITING)
async def update(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="Id Of The Module"),
    type: str = Query(..., description="type should be module or permission"),
    user: dict = Depends(UserAuthenticatorMiddleware),
    role_module_id: str = Query(..., description="Id Of The Module"),
):
    try:

        if type not in ["module", "permission"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "type should be module or permission",
                    "success": False,
                },
            )

        cache_data_key = f"organization_roles_permissions_fetch_role_{role_module_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        if type == "module":
            role_permission_module = (
                db.query(Models.RoleAssociatedPermissionModule)
                .filter(Models.RoleAssociatedPermissionModule.id == id)
                .options(
                    joinedload(Models.RoleAssociatedPermissionModule.permissions),
                    joinedload(Models.RoleAssociatedPermissionModule.sub_modules),
                    joinedload(Models.RoleAssociatedPermissionModule.sub_modules).joinedload(
                        Models.RoleAssociatedPermissionModule.sub_modules
                    ),
                    joinedload(Models.RoleAssociatedPermissionModule.sub_modules).joinedload(
                        Models.RoleAssociatedPermissionModule.permissions
                    ),
                )
                .first()
            )
            if not role_permission_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Module Not Found",
                        "success": False,
                    },
                )

            if role_permission_module.is_active:
                role_permission_module.is_active = False

                for permission in role_permission_module.permissions:
                    if permission.show_input:
                        permission.is_allowed = False

                for sub_module in role_permission_module.sub_modules:
                    deactivate_module(sub_module)

            else:
                role_permission_module.is_active = True

            db.commit()

            return {
                "success": True,
                "message": "Role Updated Successfully",
                "data": role_permission_module,
            }
        else:
            permission = (
                db.query(Models.PermissionModule).filter(Models.PermissionModule.id == id).first()
            )

            if not permission:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Permission Not Found",
                        "success": False,
                    },
                )

            permission.is_allowed = False if permission.is_allowed else True

            db.commit()

            return {
                "success": True,
                "message": "Permission Successfully",
                "permission": model_to_filtered_dict(permission),
            }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        db.rollback()  # ✅ Ensure rollback in case of error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Updating The Role And Permission",
                "success": False,
                "error": str(e),
            },
        )


# * ------------------------- The Api To Add A New Role  -------------------
@configRoute.post("/roles_permissions/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Add_Edit_Roles_Permissions(
    request: Request,
    db: db_dependencies,
    data: AddRolesPermission,
    type: str = Query("add", description="The Type Should Be Add Edit"),
    edit_role_id: Optional[str] = Query(
        None, description="The Edit Role Id Is Required To Edit Role"
    ),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        if type.lower() not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "The Type Should Be Add Edit",
                    "success": False,
                },
            )

        cache_data_key = f"organization_roles_permissions_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
        )

        if type.lower() == "add":

            clone_role_id = data.clone_role_info.clone_role_id
            config_module_id = data.clone_role_info.config_module_id

            if not clone_role_id or not config_module_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": (
                            "The Clone Role Id Is Required"
                            if clone_role_id
                            else "The Config Module Id Is Required"
                        ),
                        "success": False,
                    },
                )
            existing_role = (
                db.query(Models.ConfigRoleModule)
                .filter(func.lower(Models.ConfigRoleModule.role_name) == func.lower(data.role_name))
                .first()
            )

            if existing_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Designations Is Already Exist",
                        "success": False,
                    },
                )

            role_permission_module = (
                db.query(Models.RoleAssociatedPermissionModule)
                .filter(Models.RoleAssociatedPermissionModule.role_module_id == clone_role_id)
                .options(
                    joinedload(Models.RoleAssociatedPermissionModule.permissions),
                    joinedload(Models.RoleAssociatedPermissionModule.sub_modules),
                )
                .all()
            )
            if not role_permission_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Role not found",
                        "success": False,
                    },
                )

            created_by_user = model_to_filtered_dict(
                personal_info, ["user_id", "first_name", "last_name"]
            )

            config_role_module = Models.ConfigRoleModule(
                role_name=data.role_name,
                description=data.description,
                is_editable=True,
                status=data.status,
                source_type="user_created",
                config_module_id=config_module_id,
                created_by=json.dumps(created_by_user),
            )
            db.add(config_role_module)
            db.flush()

            modules = build_hierarchy(role_permission_module)

            for module in modules:

                permission_module = recursive_creation_helper(
                    module, db, role_module_id=config_role_module.id
                )

                config_role_module.associated_permissions.append(permission_module)

            db.commit()

            return {
                "success": True,
                "message": f"The Role Added SuccessFully",
            }
        else:
            if type == "edit" and not edit_role_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "The Edit Role Id Is Required",
                        "success": False,
                    },
                )

            existing_role_module = (
                db.query(Models.ConfigRoleModule)
                .filter(
                    func.lower(Models.ConfigRoleModule.role_name) == func.lower(data.role_name),
                    Models.ConfigRoleModule.id != edit_role_id,
                )
                .first()
            )

            if existing_role_module:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Designations Is Already Exist",
                        "success": False,
                    },
                )

            update_by_user = model_to_filtered_dict(
                personal_info, ["user_id", "first_name", "last_name"]
            )

            config_role_module = (
                db.query(Models.ConfigRoleModule)
                .filter(Models.ConfigRoleModule.id == edit_role_id)
                .first()
            )

            config_role_module.role_name = data.role_name
            config_role_module.description = data.description
            config_role_module.status = data.status
            config_role_module.updated_by = json.dumps(update_by_user)

            db.commit()

            return {"success": True, "message": "Roles Permission Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Something Went Wrong",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.delete(path="/roles_permissions/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Delete_Roles_Permission(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="The Id Is Required To Delete a Role Module"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_roles_permissions_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        config_role_module = (
            db.query(Models.ConfigRoleModule).filter(Models.ConfigRoleModule.id == id).first()
        )

        if not config_role_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No Such Config Role Module Found",
                    "success": False,
                },
            )
        db.query(Models.RoleAssociatedPermissionModule).filter(
            Models.RoleAssociatedPermissionModule.parent_module_id == id
        ).delete(synchronize_session=False)

        # Delete all associated permission entries for the role_module_id
        db.query(Models.RoleAssociatedPermissionModule).filter(
            Models.RoleAssociatedPermissionModule.role_module_id == id
        ).delete(synchronize_session=False)
        db.delete(config_role_module)
        db.commit()

        return {"success": True, "message": "Roles Permission Deleted Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        db.rollback()  # ✅ Ensure rollback in case of error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Deleting The Role",
                "success": False,
                "error": str(e),
            },
        )


# ? ------------------------- This Is The Api For The Client Form Schema  -------------------


@configRoute.get("/inquiry_form_schema/fetch")
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Inquiry_Form_Schema(
    request: Request,
    db: db_dependencies,
    order: str = Query("asc", alias="order"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_inquiry_form_schema_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)
            cached_sorted_data = sorted(
                cached_Data,
                key=lambda x: datetime.fromisoformat(x["created_at"]),
                reverse=True if order.lower() == "desc" else False,
            )
            return {
                "message": "Inquiry Form Schema Fetched Successfully. Cached!",
                "success": True,
                "data": cached_sorted_data,
            }

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )
        sort_order = order.lower()

        sort_func = asc if sort_order == "asc" else desc

        inquiry_form_schemas = (
            db.query(Models.InquiryFormSchema)
            .filter(Models.InquiryFormSchema.config_module_id == config_module.id)
            .order_by(sort_func(Models.InquiryFormSchema.created_at))
        )

        data = [model_to_filtered_dict(inquiry_form) for inquiry_form in inquiry_form_schemas]

        await cache_database.set(cache_data_key, json.dumps(jsonable_encoder(data)), ex=3600)

        return {
            "success": True,
            "message": "Inquiry Form Schema Fetched Successfully",
            "data": data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        db.rollback()  # ✅ Ensure rollback in case of error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Fetching The Client Form Schema",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.post(path="/inquiry_form_schema/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Add_Edit_Inquiry_Form_Schema(
    request: Request,
    db: db_dependencies,
    data: InquiryFormSchemaSchemaModel,
    type: str = Query(..., description="type Should be 'add' , 'edit'"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )
        cache_data_key = f"organization_inquiry_form_schema_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
        )

        query = db.query(Models.InquiryFormSchema).filter(
            or_(
                func.lower(Models.InquiryFormSchema.form_id) == func.lower(data.form_id),
                func.lower(Models.InquiryFormSchema.form_name) == func.lower(data.form_name),
            )
        )

        if type == "edit" and id:
            query = query.filter(
                Models.InquiryFormSchema.id != id,
            )

        existing_form = query.first()

        if existing_form:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Form Schema Already Exist",
                    "success": False,
                },
            )

        created_updated_by_user = model_to_filtered_dict(
            personal_info, ["user_id", "first_name", "last_name"]
        )

        if type == "add":

            config_module = (
                db.query(Models.ConfigModule)
                .filter(Models.ConfigModule.organization_id == user.organization_id)
                .first()
            )

            if not config_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Config Module Not Found", "success": False},
                )

            inquiry_form = Models.InquiryFormSchema(
                form_id=data.form_id,
                form_name=data.form_name,
                status=data.status,
                description=data.description,
                authorized_recipient_emails=json.dumps(data.authorized_recipient_emails),
                email_notification=data.email_notification,
                source_type="user_created",
                config_module_id=config_module.id,
                created_by=json.dumps(created_updated_by_user),
                updated_by=None,
            )

            db.add(inquiry_form)
            db.commit()

            return {"success": True, "message": "Form Added Successfully"}

        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            inquiry_form = (
                db.query(Models.InquiryFormSchema).filter(Models.InquiryFormSchema.id == id).first()
            )

            if not inquiry_form:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Form Not Found", "success": False},
                )

            inquiry_form.form_id = data.form_id
            inquiry_form.form_name = data.form_name
            inquiry_form.status = data.status
            inquiry_form.description = data.description
            inquiry_form.updated_by = json.dumps(created_updated_by_user)
            inquiry_form.authorized_recipient_emails = json.dumps(data.authorized_recipient_emails)

            inquiry_form.email_notification = data.email_notification

            db.commit()

            return {"success": True, "message": "Form Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add , Edit Field Right Now",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.put(
    path="/inquiry_form_schema/toggle/email-notification", status_code=status.HTTP_200_OK
)
@limiter.limit(API_RATE_LIMITING)
async def delete_designation(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="ID for delete operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_inquiry_form_schema_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        inquiry_form = (
            db.query(Models.InquiryFormSchema).filter(Models.InquiryFormSchema.id == id).first()
        )

        if not inquiry_form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Form Not Found", "success": False},
            )

        inquiry_form.email_notification = True if not inquiry_form.email_notification else False

        db.commit()

        status = "enabled" if inquiry_form.email_notification else "disabled"

        return {"success": True, "message": f"Email notifications have been {status} successfully."}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Delete Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.delete(path="/inquiry_form_schema/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def delete_designation(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="ID for delete operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_inquiry_form_schema_{user.organization_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        inquiry_form_field = (
            db.query(Models.InquiryFormSchema).filter(Models.InquiryFormSchema.id == id).first()
        )

        if not inquiry_form_field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Form Not Found", "success": False},
            )

        db.delete(inquiry_form_field)
        db.commit()

        return {"success": True, "message": "Form Deleted Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Delete Status Right Now",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.get("/inquiry_form_fields/fetch")
@limiter.limit(API_RATE_LIMITING)
async def Client_Form_Schema(
    request: Request,
    db: db_dependencies,
    form_schema_id: str = Query(..., alias="form_schema_id"),
    order: str = Query("asc", alias="order"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_inquiry_form_fields_{form_schema_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)
            cached_sorted_data = sorted(
                cached_Data.get("form_fields"),
                key=lambda x: datetime.fromisoformat(x["created_at"]),
                reverse=True if order.lower() == "desc" else False,
            )
            cached_Data["form_fields"] = cached_sorted_data
            return {
                "message": "Inquiry Form Fields Fetched Successfully. Cached!",
                "success": True,
                "data": cached_Data,
            }

        config_module = (
            db.query(Models.ConfigModule)
            .filter(Models.ConfigModule.organization_id == user.organization_id)
            .first()
        )

        if not config_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config Module Not Found",
                    "success": False,
                },
            )

        inquiry_form_schema = (
            db.query(Models.InquiryFormSchema)
            .filter(Models.InquiryFormSchema.id == form_schema_id)
            .first()
        )

        if not inquiry_form_schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Form Schema Not Found",
                    "success": False,
                },
            )

        sort_order = order.lower()

        sort_func = asc if sort_order == "asc" else desc

        form_fields = (
            db.query(Models.InquiryFormFields)
            .filter(Models.InquiryFormFields.inquiry_form_schema_id == inquiry_form_schema.id)
            .order_by(sort_func(Models.InquiryFormFields.created_at))
        )

        data = [model_to_filtered_dict(field) for field in form_fields]

        filtered_data: dict = {
            **model_to_filtered_dict(inquiry_form_schema, fields=["form_id", "form_name"]),
            "form_fields": data,
        }

        await cache_database.set(
            cache_data_key, json.dumps(jsonable_encoder(filtered_data)), ex=3600
        )

        return {
            "success": True,
            "message": "Inquiry Form Fields Fetched Successfully",
            "data": filtered_data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        db.rollback()  # ✅ Ensure rollback in case of error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Fetching The Client Form Schema",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.post(path="/inquiry_form_fields/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def add_edit_Client_Form_Schema(
    request: Request,
    db: db_dependencies,
    data: ClientFormSchemaModel,
    type: str = Query(..., description="type Should be 'add' , 'edit'"),
    form_schema_id: str = Query(..., alias="form_schema_id"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_inquiry_form_fields_{form_schema_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
        )

        inquiry_form_schema = (
            db.query(Models.InquiryFormSchema)
            .filter(Models.InquiryFormSchema.id == form_schema_id)
            .first()
        )

        if not inquiry_form_schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Form Schema Not Found", "success": False},
            )

        query = db.query(Models.InquiryFormFields).filter(
            and_(
                func.lower(Models.InquiryFormFields.field_name) == func.lower(data.field_name),
                Models.InquiryFormFields.inquiry_form_schema_id == inquiry_form_schema.id,
            )
        )

        if type == "edit" and id:
            query = query.filter(
                Models.InquiryFormFields.id != id,
            )

        if query.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Field With This Name Is Already Exist",
                    "success": False,
                },
            )

        created_updated_by_user = model_to_filtered_dict(
            personal_info, ["user_id", "first_name", "last_name"]
        )

        if type == "add":

            config_module = (
                db.query(Models.ConfigModule)
                .filter(Models.ConfigModule.organization_id == user.organization_id)
                .first()
            )

            if not config_module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Config Module Not Found", "success": False},
                )

            form_field = Models.InquiryFormFields(
                field_name=data.field_name,
                is_required_field=data.is_required_field,
                type=data.type,
                source_type="user_created",
                inquiry_form_schema_id=inquiry_form_schema.id,
                created_by=json.dumps(created_updated_by_user),
                updated_by=None,
            )

            db.add(form_field)
            db.commit()

            return {"success": True, "message": "Field Added Successfully"}

        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            form_field = (
                db.query(Models.InquiryFormFields).filter(Models.InquiryFormFields.id == id).first()
            )

            if not form_field:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Field Not Found", "success": False},
                )

            form_field.field_name = data.field_name
            form_field.is_required_field = data.is_required_field
            form_field.type = data.type
            form_field.updated_by = json.dumps(created_updated_by_user)

            db.commit()

            return {"success": True, "message": "Field Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add , Edit Field Right Now",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.delete(path="/inquiry_form_fields/delete", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def delete_designation(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., description="ID for delete operation"),
    form_schema_id: str = Query(..., alias="form_schema_id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        cache_data_key = f"organization_inquiry_form_fields_{form_schema_id}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            await cache_database.delete(cache_data_key)

        inquiry_form_schema = (
            db.query(Models.InquiryFormSchema)
            .filter(Models.InquiryFormSchema.id == form_schema_id)
            .first()
        )

        if not inquiry_form_schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Form Schema Not Found", "success": False},
            )
        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

        inquiry_form_field = (
            db.query(Models.InquiryFormFields)
            .filter(
                and_(
                    Models.InquiryFormFields.id == id,
                    Models.InquiryFormFields.inquiry_form_schema_id == form_schema_id,
                )
            )
            .first()
        )

        if not inquiry_form_field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Filed Not Found", "success": False},
            )

        db.delete(inquiry_form_field)
        db.commit()

        return {"success": True, "message": "Field Deleted Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Delete Status Right Now",
                "success": False,
                "error": str(e),
            },
        )
