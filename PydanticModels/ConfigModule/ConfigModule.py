from pydantic import BaseModel


class ProjectStatus(BaseModel):
    status_name: str
    status_color: str


class AttachmentType(BaseModel):
    attachment_name: str


class Designations(BaseModel):
    designations_name: str
