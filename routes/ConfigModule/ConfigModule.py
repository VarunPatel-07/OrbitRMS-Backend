from fastapi import APIRouter, Depends, HTTPException, Query, status

from typing import Optional

from Database.Database import db_dependencies
from PydanticModels.ConfigModule.ConfigModule import ProjectStatus
from Middleware.verifyToken import verify_token
from SqlModels import Models
from Helper.createModelInstance import cerate_model_instance


configRoute = APIRouter(prefix="/app/v1/config", tags=["config"])


@configRoute.post(path="/project_status/add-edit", status_code=status.HTTP_200_OK)
async def project_status_function(
    db: db_dependencies,
    data: ProjectStatus,
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

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Not Found",
                    "success": False,
                },
            )
        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Invalid type. Must be 'add' or 'edit'"},
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
                config_module_id=config_module.id,
            )

            db.add(project_status)
            db.commit()
            db.refresh(project_status)

            return {"success": True, "message": "Project Status Added Successfully"}
        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "ID is required for edit operation"},
                )

            project_status = (
                db.query(Models.ProjectStatus).filter(Models.ProjectStatus.id == id).first()
            )

            if not project_status:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Project Status Not Found"},
                )

            project_status.status_name = data.status_name
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
            "data": [each_project_status for each_project_status in project_status],
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


@configRoute.post(path="/project_status/delete", status_code=status.HTTP_200_OK)
async def delete_project_status(
    db: db_dependencies,
    token: str = Depends(verify_token),
    id: str = Query(..., description="ID for edit operation"),
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
                "message": "Unable To Add Status Right Now",
                "success": False,
                "error": str(e),
            },
        )
