from fastapi import HTTPException, status

from constants.constant import SUCCESS
from database.Database import db_dependencies
from jobs.backgroundHandler.DataSeederHelper import recursive_creation_helper
from models.sql import Models
from routes.admin.rolePermissionSync.crude import build_role_module_index, fetch_config_modules, fetch_org_roles
from routes.admin.rolePermissionSync.utils import disable_all_permissions, load_default_roles_permission_json
from database.CacheDatabase import cache_database


def sync_role_modules(
    db: db_dependencies,
    role: Models.ConfigRoleModule,
    template_modules: list,
    path: str,
    module_index: dict,
    parent_module_id: str,
    grant_permissions: bool,
    changes: list,
):
    for template in template_modules:
        module_path = f"{path}/{template.module_label}" if path else template.module_label
        existing = module_index.get((parent_module_id, template.module_label))

        if not existing:
            new_module = template if grant_permissions else disable_all_permissions(template)
            created = recursive_creation_helper(
                module_data=new_module, db=db, role_module_id=role.id, parent_module_id=parent_module_id
            )

            if parent_module_id is None:
                role.associated_permissions.append(created)

            changes.append({"type": "module_added", "path": module_path})
            continue

        existing_labels = {permission.label for permission in existing.permissions}
        for permission in template.permissions:
            if permission.label in existing_labels:
                continue

            db.add(
                Models.PermissionModule(
                    label=permission.label,
                    is_allowed=permission.is_allowed if grant_permissions else False,
                    show_input=permission.show_input,
                    associated_permissions_module_id=existing.id,
                )
            )

            changes.append({"type": "permission_added", "path": module_path, "permission": permission.label})

        sync_role_modules(
            db=db,
            role=role,
            template_modules=template.sub_modules,
            path=module_path,
            module_index=module_index,
            parent_module_id=existing.id,
            grant_permissions=grant_permissions,
            changes=changes,
        )


async def syncRolesAndPermissionServiceWorker(db: db_dependencies, dry_run: bool, token):
    load_default_roles = load_default_roles_permission_json()
    admin_template = load_default_roles.get("administrator")

    if not admin_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Administrator Role is missing in the default JSON", "success": SUCCESS.FALSE},
        )

    summary = {"organizations_scanned": 0, "roles_scanned": 0, "updated": [], "failed": []}

    config_modules = fetch_config_modules(db)

    for config_module in config_modules:
        summary["organizations_scanned"] += 1

        org_changes = []
        try:
            roles = fetch_org_roles(db=db, config_module_id=config_module.id)

            for role in roles:
                summary["roles_scanned"] += 1

                # Default Roles Present In JSON Use Their Own Tree, Everything Else Gets Admin Tree With Permissions Off

                default_role = load_default_roles.get(role.role_name.lower()) if role.source_type == "default" else None

                template = default_role or admin_template
                grant_permissions = default_role is not None

                role_changes = []

                sync_role_modules(
                    db=db,
                    parent_module_id=None,
                    template_modules=template.permission_modules,
                    role=role,
                    changes=role_changes,
                    grant_permissions=grant_permissions,
                    module_index=build_role_module_index(db, role.id),
                    path="",
                )

                #  sync_role_modules(
                #                     db,
                #                     role,
                #                     template.permission_modules,
                #                     build_role_module_index(db, role.id),
                #                     grant_permissions=grant_permissions,
                #                     path="",
                #                     changes=role_changes,
                #                 )

                if role_changes:
                    org_changes.append({"role_id": role.id, "role_name": role.role_name, "changes": role_changes})

                if dry_run or not org_changes:
                    db.rollback()
                else:
                    db.commit()

                    await cache_database.delete(f"organization_roles_permissions_{config_module.organization_id}")

                    for role in roles:
                        await cache_database.delete(f"organization_roles_permissions_fetch_role_{role.id}")

                if org_changes:
                    summary["updated"].append({"organization_id": config_module.organization_id, "roles": org_changes})

        except Exception as e:
            db.rollback()
            summary["failed"].append({"organization_id": config_module.organization_id, "error": str(e)})

    return {
        "success": SUCCESS.TRUE,
        "message": "Dry run completed" if dry_run else "Roles permissions synced successfully",
        "data": summary,
    }
