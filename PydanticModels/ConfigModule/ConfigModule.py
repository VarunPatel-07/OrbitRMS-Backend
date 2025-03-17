from pydantic import BaseModel


class ProjectStatus(BaseModel):
    status_name: str
