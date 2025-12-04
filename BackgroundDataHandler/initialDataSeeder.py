import json
import os

from fastapi import HTTPException, status

from BackgroundDataHandler.DataSeederHelper import (
    client_form_filed_data_seeder_helper_function,
    department_data_seeder_helper_function,
    designation_data_seeder_helper_function,
    project_status_data_seeder_helper_function,
    roles_permission_data_seeder_helper,
)
from PydanticModels.ConfigModule.ConfigModule import (
    AddRolesPermission,
    ClientFormSchemaModel,
    Department,
    Designations,
    InquiryFormSchemaSchemaModel,
    ProjectStatus,
    RoleAssociatedPermissionModule,
    RolesPermission,
)


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


def designation_initial_data_seeder(db, organization_id: str, industry_slug: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "data", "defaultDesignationsData.json")

    try:
        with open(path, "r") as file_content:

            data_dict = json.load(file_content)

            if not isinstance(data_dict, dict):
                raise ValueError("Expected a dict of designations")
            
            industry_data = data_dict.get(industry_slug)
            if industry_data is None:
                raise ValueError(f"Industry '{industry_slug}' not found in JSON file")

            if not isinstance(industry_data, list):
                raise ValueError("Industry data must be a list of designations")


            for each_data in industry_data:
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


def department_data_initial_data_seeder(db, organization_id: str, industry_slug: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "data", "defaultDepartmentData.json")

    try:
        with open(path, "r") as file_content:

            data_dict = json.load(file_content)

            if not isinstance(data_dict, dict):
                raise ValueError("Expected a dictionary of industries")
            
            industry_data = data_dict.get(industry_slug)
            if industry_data is None:
                raise ValueError(f"Industry '{industry_slug}' not found in JSON file")

            if not isinstance(industry_data, list):
                raise ValueError("Industry data must be a list of departments")

            for each_data in industry_data:
                if not isinstance(each_data, dict):
                    raise ValueError("Each department should be a dictionary")

                if "department_name" not in each_data:
                    raise ValueError("Missing 'department_name' in department data")

                try:
                    department_data = Department(**each_data)
                    department_data_seeder_helper_function(db, organization_id, department_data)

                except HTTPException as http_exception:
                    raise http_exception
                except Exception as e:

                    raise ValueError(f"Invalid department data: {str(e)}")

    except HTTPException as http_exception:
        raise http_exception
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Default department data file not found", "success": False},
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


def client_form_field_initial_data_seeder(db, organization_id: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "data", "defaultClientFormFields.json")

    try:
        with open(path, "r") as file_content:

            file_data = json.load(file_content)

            if not isinstance(file_data, dict):
                raise ValueError("Each Form should be a dictionary")

            if "form_schema" not in file_data:
                raise ValueError("Missing 'form_schema' in Client Form Field data")

            if "form_fields" not in file_data:
                raise ValueError("Missing 'form_field' in Client Form Field data")

            try:

                form_field_data_array = []

                for form_field in file_data["form_fields"]:

                    if not isinstance(form_field, dict):
                        raise ValueError("Each department should be a dictionary")

                    if "field_name" not in form_field:
                        raise ValueError("Missing 'field_name' in Client Form Field data")

                    if "is_required_field" not in form_field:
                        raise ValueError("Missing 'is_required_field' in Client Form Field data")

                    if "type" not in form_field:
                        raise ValueError("Missing 'type' in Client Form Field data")

                    form_field_data_array.append(ClientFormSchemaModel(**form_field))

                form_field_data = InquiryFormSchemaSchemaModel(**file_data["form_schema"])
                client_form_filed_data_seeder_helper_function(
                    db, organization_id, form_field_data, form_field_data_array
                )

            except HTTPException as http_exception:
                raise http_exception
            except Exception as e:
                raise ValueError(f"Invalid Form data: {str(e)}")

    except HTTPException as http_exception:
        raise http_exception
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Default department data file not found", "success": False},
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
