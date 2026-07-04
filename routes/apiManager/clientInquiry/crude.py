from database.Database import db_dependencies
from models.sql import Models


async def get_client_inquiry(db: db_dependencies, org_id: str | None = None, inquiry_id: str | None = None):

    if inquiry_id:

        client_inquires = db.query(Models.ClientInquires).filter(Models.ClientInquires.id == inquiry_id).first()

        return client_inquires

    if org_id:

        client_inquires = (
            db.query(Models.ClientInquires).filter(Models.ClientInquires.organization_id == org_id).first()
        )

        return client_inquires


async def get_inquiry_forms_data(db: db_dependencies, org_id: str):
    config_module = db.query(Models.ConfigModule).filter(Models.ConfigModule.organization_id == org_id).first()

    inquiry_forms = (
        db.query(Models.InquiryFormSchema).filter(Models.InquiryFormSchema.config_module_id == config_module.id).all()
    )

    return inquiry_forms


async def fetch_inquiry_form(db: db_dependencies, inquiry_form_id: str):
    inquiry_forms = db.query(Models.InquiryFormSchema).filter(Models.InquiryFormSchema.id == inquiry_form_id).first()

    return inquiry_forms
