import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func


# Import database dependencies and helper functions
from sqlalchemy.orm import joinedload
from Database.Database import db_dependencies
from Helper.createModelInstance import cerate_model_instance
from Helper.helper import model_to_filtered_dict
from Middleware.verifyToken import verify_token
from PydanticModels.ConfigModule.ConfigModule import (
    AttachmentType,
    Designations,
    ProjectStatus,
    RolesPermission,
    RoleAssociatedPermissionModule,
)
from SqlModels import Models
from BackgroundDataHandler.initialDataSeeder import roles_permission_initial_data_seeder_function

configRoute = APIRouter(prefix="/app/v1/config", tags=["config"])


#  ----- All The Crud Api For The Project Status Start From Here -----


# ?  (1)  API To Add/Edit " Project Status "


@configRoute.post(path="/project_status/add-edit", status_code=status.HTTP_200_OK)
async def project_status_function(
    db: db_dependencies,
    data: ProjectStatus,
    token: str = Depends(verify_token),
    type: str = Query(..., description="Operation type: add or edit"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
):
    try:
        # Checking For The Valid Token
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
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

            existing_status = (
                db.query(Models.ProjectStatus)
                .filter(
                    func.lower(Models.ProjectStatus.status_name) == func.lower(data.status_name)
                )
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

            created_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )

            project_status = Models.ProjectStatus(
                status_name=data.status_name,
                source_type="user_created",
                status_color=data.status_color,
                config_module_id=config_module.id,
                created_by=json.dumps(created_by_user),
                updated_by=None,
            )

            db.add(project_status)
            db.commit()
            db.refresh(project_status)

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

            existing_status = (
                db.query(Models.ProjectStatus)
                .filter(
                    func.lower(Models.ProjectStatus.status_name) == func.lower(data.status_name),
                    Models.ProjectStatus.id != id,
                )
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

            updated_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )
            project_status.status_name = data.status_name
            project_status.updated_by = json.dumps(updated_by_user)
            project_status.status_color = data.status_color
            db.commit()
            db.refresh(project_status)

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
async def fetch_project_status(db: db_dependencies, token: str = Depends(verify_token)):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )

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

        project_status = db.query(Models.ProjectStatus).filter(
            Models.ProjectStatus.config_module_id == config_module.id
        )

        return {
            "success": True,
            "message": "Project Status Fetched Successfully",
            "data": [
                model_to_filtered_dict(each_project_status)
                for each_project_status in project_status
            ],
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
async def delete_project_status(
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., description="ID for delete operation"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )
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


# *  ----- All The Crud Api For The Attachment Type Start From Here -----

# ?  (4)  API To Add/Edit " Attachment Type "


@configRoute.post(path="/attachment_type/add-edit", status_code=status.HTTP_200_OK)
async def add_edit_attachment_type(
    db: db_dependencies,
    data: AttachmentType,
    token: str = Depends(verify_token),
    type: str = Query(..., description="Operation type: add or edit"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )
        user_id = token["user_id"]

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
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

            existing_attachment_type = (
                db.query(Models.AttachmentType)
                .filter(
                    func.lower(Models.AttachmentType.attachment_name)
                    == func.lower(data.attachment_name)
                )
                .first()
            )

            if existing_attachment_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Attachment With This Name Is Already Exist",
                        "success": False,
                    },
                )

            created_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )

            attachment_type = Models.AttachmentType(
                attachment_name=data.attachment_name,
                config_module_id=config_module.id,
                source_type="user_created",
                created_by=json.dumps(created_by_user),
                updated_by=None,
            )

            db.add(attachment_type)
            db.commit()
            db.refresh(attachment_type)

            return {"success": True, "message": "Attachment Created Successfully"}
        else:

            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            existing_attachment_type = (
                db.query(Models.AttachmentType)
                .filter(
                    func.lower(Models.AttachmentType.attachment_name)
                    == func.lower(data.attachment_name),
                    Models.AttachmentType.id != id,
                )
                .first()
            )

            if existing_attachment_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Attachment With This Name Is Already Exist",
                        "success": False,
                    },
                )

            attachment_type = (
                db.query(Models.AttachmentType).filter(Models.AttachmentType.id == id).first()
            )

            if not attachment_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "No Such Attachment Found", "success": False},
                )
            updated_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )
            attachment_type.attachment_name = data.attachment_name
            attachment_type.updated_by = json.dumps(updated_by_user)
            db.commit()
            db.refresh(attachment_type)

            return {"success": True, "message": "Attachment Updated Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Add Attachment Type Right Now",
                "success": False,
                "error": str(e),
            },
        )


# ?  (5)  API To Fetch " Attachment Type "


@configRoute.get(path="/attachment_type/fetch", status_code=status.HTTP_200_OK)
async def fetch_all_attachment_type(db: db_dependencies, token: str = Depends(verify_token)):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )

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

        attachment_type = db.query(Models.AttachmentType).filter(
            Models.AttachmentType.config_module_id == config_module.id
        )

        return {
            "success": True,
            "message": "Attachment Type Fetched Successfully",
            "data": [
                model_to_filtered_dict(each_attachment_type)
                for each_attachment_type in attachment_type
            ],
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


# ?  (6)  API To Delete " Attachment Type "


@configRoute.delete(path="/attachment_type/delete", status_code=status.HTTP_200_OK)
async def delete_attachment_type(
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., description="ID for delete operation"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )

        attachment_type = (
            db.query(Models.AttachmentType).filter(Models.AttachmentType.id == id).first()
        )

        if not attachment_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Attachment Not Found",
                    "success": False,
                },
            )

        db.delete(attachment_type)
        db.commit()

        return {"success": True, "message": "Attachment Deleted Successfully"}

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


# *  ----- All The Crud Api For The Attachment Type End Here -----


#  ----- All The Crud Api For The Designations Start From Here -----


# ?  (7)  API To Add/Edit " Designations "


@configRoute.post(path="/designations/add-edit", status_code=status.HTTP_200_OK)
async def add_edit_designations(
    db: db_dependencies,
    data: Designations,
    token: str = Depends(verify_token),
    type: str = Query(..., description="type Should be 'add' , 'edit'"),
    id: Optional[str] = Query(None, description="ID for edit operation"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": "Invalid type. Must be 'add' or 'edit'",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "User Not Found", "success": False},
            )

        personal_info = (
            db.query(Models.PersonalInfo).filter(Models.PersonalInfo.user_id == user.id).first()
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

            existing_designations = (
                db.query(Models.Designations)
                .filter(
                    func.lower(Models.Designations.designations_name)
                    == func.lower(data.designations_name)
                )
                .first()
            )

            if existing_designations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Designations Is Already Exist",
                        "success": False,
                    },
                )

            created_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )

            designations = Models.Designations(
                designations_name=data.designations_name,
                source_type="user_created",
                config_module_id=config_module.id,
                created_by=json.dumps(created_by_user),
                updated_by=None,
            )

            db.add(designations)
            db.commit()
            db.refresh(designations)

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

            existing_designations = (
                db.query(Models.Designations)
                .filter(
                    func.lower(Models.Designations.designations_name)
                    == func.lower(data.designations_name)
                )
                .first()
            )

            if existing_designations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Attachment With This Name Is Already Exist",
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

            updated_by_user = model_to_filtered_dict(
                personal_info, ["id", "first_name", "last_name"]
            )

            designations.designations_name = data.designations_name
            designations.updated_by = json.dumps(updated_by_user)

            db.commit()
            db.refresh(designations)

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
async def fetch_all_designations(db: db_dependencies, token: str = Depends(verify_token)):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "User Not Found", "success": False},
            )

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

        designations = db.query(Models.Designations).filter(
            Models.Designations.config_module_id == config_module.id
        )

        return {
            "message": "Designation Fetched Successfully",
            "success": True,
            "data": [model_to_filtered_dict(each_designation) for each_designation in designations],
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
async def delete_designation(
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., description="ID for delete operation"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )
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
    module: RoleAssociatedPermissionModule,
    db: db_dependencies,
    role_module_id,
    parent_module_id: Optional[str] = None,
):
    try:
        parent_module = Models.RoleAssociatedPermissionModule(
            module_label=module.module_label,
            module_title=module.module_title,
            is_active=module.is_active,
            parent_module_id=parent_module_id,
            role_module_id=role_module_id,
        )

        db.add(parent_module)
        db.flush()  #

        for permission in module.permissions:
            permission_module = Models.PermissionModule(
                label=permission.label,
                is_allowed=permission.is_allowed,
                show_input=permission.show_input,
                associated_permissions_module_id=parent_module.id,
            )

            db.add(permission_module)

        for submodule in module.sub_modules:
            recursive_creation_helper(
                submodule, db, role_module_id, parent_module.id  # Set parent ID for submodules
            )

        return parent_module
    except Exception as e:
        db.rollback()  # ✅ Ensure rollback in case of error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Adding The Role And Permission",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.post(path="/roles_permissions/add", status_code=status.HTTP_200_OK)
async def add_role_permission(
    db: db_dependencies,
    data: RolesPermission,
    organization_id: str = Query(None, description="ID for edit operation"),
):
    try:
        roles_permission_initial_data_seeder_function(db, organization_id)
        return {
            "message": "Role and permissions added successfully",
            "role_name": data.role_name,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error While Adding The Role And Permission",
                "success": False,
                "error": str(e),
            },
        )


@configRoute.get("/roles_permissions/fetch-all", status_code=status.HTTP_200_OK)
async def fetch_all_role_of_organization(
    db: db_dependencies,
    token: str = Depends(verify_token),
):

    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )

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

        roles_permissions = db.query(Models.ConfigRoleModule).filter(
            Models.ConfigRoleModule.config_module_id == config_module.id
        )

        # Replace the model_to_dict part with this:

        return {
            "message": "Designation Fetched Successfully",
            "success": True,
            "data": [
                model_to_filtered_dict(role_permission) for role_permission in roles_permissions
            ],
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


@configRoute.get("/roles_permissions/fetch-role", status_code=status.HTTP_200_OK)
async def fetch_roles_permission(
    db: db_dependencies, role_id: str = Query(..., description="ID of the role to fetch")
):
    try:
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
            raise HTTPException(status_code=404, detail="Role not found")

        # Build hierarchy
        def build_hierarchy(modules, parent_id=None):
            result = []
            for module in modules:
                if module.parent_module_id == parent_id:
                    module_data = {
                        "id": module.id,
                        "module_label": module.module_label,
                        "module_title": module.module_title,
                        "is_active": module.is_active,
                        "permissions": [
                            {
                                "id": p.id,
                                "label": p.label,
                                "is_allowed": p.is_allowed,
                                "show_input": p.show_input,
                            }
                            for p in module.permissions
                        ],
                        "sub_modules": build_hierarchy(modules, module.id),
                    }
                    result.append(module_data)
            return result

        # Get role details
        role = db.query(Models.ConfigRoleModule).get(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        return {
            "message": "Role fetched successfully",
            "success": True,
            "data": {
                "id": role.id,
                "role_name": role.role_name,
                "description": role.description,
                "source_type": role.source_type,
                "created_by": role.created_by,
                "created_at": role.created_at,
                "updated_by": role.updated_by,
                "updated_at": role.updated_at,
                "modules": build_hierarchy(all_modules),
            },
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


@configRoute.post("/roles_permissions/update", status_code=status.HTTP_200_OK)
async def update(
    db: db_dependencies,
    id: str = Query(..., description="Id Of The Module"),
    type: str = Query(..., description="type should be module or permission"),
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

        if type == "module":

            role_permission_module = (
                db.query(Models.RoleAssociatedPermissionModule)
                .filter(Models.RoleAssociatedPermissionModule.id == id)
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

            role_permission_module.is_active = False if role_permission_module.is_active else True

            db.commit()
            db.refresh(role_permission_module)

            return {"success": True, "message": "Attachment Updated Successfully"}
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
            db.refresh(permission)

            return {
                "success": True,
                "message": "Attachment Updated Successfully",
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
