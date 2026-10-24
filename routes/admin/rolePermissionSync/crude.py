from models.sql import Models
from database.Database import db_dependencies


def fetch_config_modules(db: db_dependencies):
    config_modules = db.query(Models.ConfigModule).all()

    return config_modules


def fetch_org_roles(db: db_dependencies, config_module_id: str):
    roles = db.query(Models.ConfigRoleModule).filter(Models.ConfigRoleModule.config_module_id == config_module_id).all()

    return roles


def build_role_module_index(db, role_id: str) -> dict:
    rows = (
        db.query(Models.RoleAssociatedPermissionModule)
        .filter(Models.RoleAssociatedPermissionModule.role_module_id == role_id)
        .all()
    )
    return {(row.parent_module_id, row.module_label): row for row in rows}
