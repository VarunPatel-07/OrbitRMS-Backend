from pydantic import BaseModel
from fastapi import Form
from typing import Optional

class VerifyUrl(BaseModel):
    url: str
    meta_tag_name: str
    meta_tag_content: str
    
    @classmethod
    def as_form(
            cls,
            url: str = Form(...),
            meta_tag_name: str = Form(...),
            meta_tag_content: str = Form(...)
            ) -> "VerifyUrl":
        return cls(
            url=url,
            meta_tag_name=meta_tag_name,
            meta_tag_content=meta_tag_content
            )

class OrganizationPydenticModel(BaseModel):
    organization_url:str
    organization_name:str
    organization_password:str
    organization_logo:Optional[str] = None
    meta_tag_name: str
    meta_tag_content: str
    
    @classmethod
    def as_form(cls ,
                organization_url: str = Form(...),
                organization_name: str = Form(...),
                organization_password: str = Form(...),
                organization_logo: Optional[str] = None,
                meta_tag_name: str = Form(...),
                meta_tag_content: str = Form(...)) -> "Organization":
        return cls(organization_url=organization_url,
                   organization_name=organization_name,
                   organization_password=organization_password,
                   organization_logo=organization_logo,
                   meta_tag_name=meta_tag_name,
                   meta_tag_content=meta_tag_content)