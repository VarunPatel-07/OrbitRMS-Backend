from fastapi import HTTPException, status
from PydanticModels.ConfigModule.ConfigModule import (
    RolesPermission,
    Designations,
    AttachmentType,
    ProjectStatus,
)
from BackgroundDataHandler.DataSeederHelper import (
    roles_permission_data_seeder_helper,
    designation_data_seeder_helper_function,
    project_status_data_seeder_helper_function,
    attachment_type_data_seeder_helper_function,
)
import json
import os


def roles_permission_initial_data_seeder_function(db, organization_id: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "data", "defaultRolePermissionData.json")

    try:
        with open(path, "r") as file_content:

            data_list = json.load(file_content)

            if not isinstance(data_list, list):
                raise ValueError("Expected a list of role permissions in JSON file")

            for each_data in data_list:
                if not isinstance(each_data, dict):
                    raise ValueError("Each role permission should be a dictionary")

                if "role_name" not in each_data:
                    raise ValueError("Missing 'role_name' in role permission data")

                try:

                    role_data = RolesPermission(**each_data)
                    roles_permission_data_seeder_helper(db, organization_id, role_data)

                except HTTPException as http_exception:
                    raise http_exception
                except Exception as e:

                    raise ValueError(f"Invalid role permission data: {str(e)}")

    except HTTPException as http_exception:
        raise http_exception
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Default role permission data file not found", "success": False},
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON format in data file", "success": False},
        )

    except ValueError as val_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid data formate {str(val_error)}", "success": False},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while seeding default role permissions",
                "success": False,
                "error": str(e),
            },
        )


def designation_initial_data_seeder(db, organization_id: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "data", "defaultDesignationsData.json")

    try:
        with open(path, "r") as file_content:

            data_list = json.load(file_content)

            if not isinstance(data_list, list):
                raise ValueError("Expected a list of designations")

            for each_data in data_list:
                if not isinstance(each_data, dict):
                    raise ValueError("Each designations should be a dictionary")

                if "designations_name" not in each_data:
                    raise ValueError("Missing 'designation_name' in designation data")

                try:
                    designation_data = Designations(**each_data)
                    designation_data_seeder_helper_function(db, organization_id, designation_data)

                except HTTPException as http_exception:
                    raise http_exception
                except Exception as e:

                    raise ValueError(f"Invalid designation data: {str(e)}")

    except HTTPException as http_exception:
        raise http_exception
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Default designation data file not found", "success": False},
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON format in data file", "success": False},
        )

    except ValueError as val_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid data formate {str(val_error)}", "success": False},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while seeding default designation data",
                "success": False,
                "error": str(e),
            },
        )


def project_status_initial_data_seeder(db, organization_id: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "data", "defaultProjectStatuses.json")

    try:
        with open(path, "r") as file_content:

            data_list = json.load(file_content)

            if not isinstance(data_list, list):
                raise ValueError("Expected a list of Project Status")

            for each_data in data_list:
                if not isinstance(each_data, dict):
                    raise ValueError("Each Project Status should be a dictionary")

                if "status_name" not in each_data:
                    raise ValueError("Missing 'status_name' in Project Status data")

                try:
                    project_status_data = ProjectStatus(**each_data)
                    project_status_data_seeder_helper_function(
                        db, organization_id, project_status_data
                    )

                except HTTPException as http_exception:
                    raise http_exception
                except Exception as e:

                    raise ValueError(f"Invalid Project Status data: {str(e)}")

    except HTTPException as http_exception:
        raise http_exception
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Default Project Status data file not found", "success": False},
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON format in data file", "success": False},
        )

    except ValueError as val_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid data formate {str(val_error)}", "success": False},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while seeding default Project Status data",
                "success": False,
                "error": str(e),
            },
        )


def attachment_type_initial_data_seeder(db, organization_id: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "data", "defaultAttachmentTypes.json")

    try:
        with open(path, "r") as file_content:

            data_list = json.load(file_content)

            if not isinstance(data_list, list):
                raise ValueError("Expected a list of Attachment")

            for each_data in data_list:
                if not isinstance(each_data, dict):
                    raise ValueError("Each Attachment should be a dictionary")

                if "attachment_name" not in each_data:
                    raise ValueError("Missing 'status_name' in Attachment data")

                try:
                    attachment_type_data = AttachmentType(**each_data)
                    attachment_type_data_seeder_helper_function(
                        db, organization_id, attachment_type_data
                    )

                except HTTPException as http_exception:
                    raise http_exception
                except Exception as e:

                    raise ValueError(f"Invalid Attachment data: {str(e)}")

    except HTTPException as http_exception:
        raise http_exception
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Default Attachment data file not found", "success": False},
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON format in data file", "success": False},
        )

    except ValueError as val_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid data formate {str(val_error)}", "success": False},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while seeding default Project Status data",
                "success": False,
                "error": str(e),
            },
        )
