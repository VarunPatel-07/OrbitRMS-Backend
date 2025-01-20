from fastapi import APIRouter, Depends, HTTPException , status
from Database.Database import db_dependencies
from Middelware.verifyToken import oauth2_scheme, verify_token
from PydenticModels.Organizations.organizations import VerifyUrl
from bs4 import BeautifulSoup
from PydenticModels.Organizations.organizations import OrganizationPydenticModel
from SqlModels import Models
from Helper.helper import generate_random_secret_key
import requests

from SqlModels.Models import Organization

organization_router = APIRouter(
    prefix="/app/v1/organization",
    tags=["organization"]
    )

@organization_router.post(path='/verify-organization-url', status_code=status.HTTP_200_OK )
async def verify_organization_url(verify_url:VerifyUrl = Depends(VerifyUrl.as_form) ,token:str = Depends(oauth2_scheme)):
   try:
       token_payload = verify_token(token)
       if not token_payload:
           raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
       responses = requests.get(verify_url.url)
       responses.raise_for_status()
       html_content = responses.text
       
       soup = BeautifulSoup(html_content, "html.parser")
       
       selected_meta_tag = soup.find("meta", attrs={"name": verify_url.meta_tag_name})
       
       if selected_meta_tag:
           if selected_meta_tag.get("content") == verify_url.meta_tag_content:
               return {
                   "name": selected_meta_tag.get("name"),
                   "content": selected_meta_tag.get("content"),
                   "success": True,
                   "message": "Organization URL verified successfully"
                   }
           else:
               return {
                   "success": False,
                   "message": "Organization URL not verified successfully because of meta tag content is different"
                   }
       else:
           raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail=f"Meta tag with name '{verify_url.meta_tag_name}' not found."
               )
   except requests.exceptions.RequestException as e:
       raise HTTPException(
           status_code=status.HTTP_404_NOT_FOUND,
           detail=f"Error fetching URL: {str(e)}"
           )
   
@organization_router.post(path='/create-organization', status_code=status.HTTP_200_OK)
async def create_organization(db:db_dependencies ,organization_info:OrganizationPydenticModel = Depends(OrganizationPydenticModel.as_form) , token:str = Depends(oauth2_scheme)):
  try:
      token_payload = verify_token(token)
      if not token_payload:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid token"
              )
      find_organization = db.query(Models.Organization).filter(
          (Models.Organization.organization_name == organization_info.organization_name) | (
                      Models.Organization.organization_url == organization_info.organization_url)
          ).first()
      if find_organization:
          raise HTTPException(
              status_code=status.HTTP_409_CONFLICT,
              detail="Organization already exists"
              )
      
      unique_organization_secret = generate_random_secret_key()
      
      new_organization = Models.Organization(
              organization_name=organization_info.organization_name,
              organization_url=organization_info.organization_url,
              organization_secret=unique_organization_secret,
              organization_logo=organization_info.organization_logo or "",
              organization_password=organization_info.organization_password,
              owner_id=token_payload,
              meta_tag_name=organization_info.organization_name,
              meta_tag_content=organization_info.meta_tag_name,
      )
      db.add(new_organization)
      db.commit()
      db.refresh(new_organization)
      
      organization_details = {
          "organization_name": new_organization.organization_name,
          "organization_url": new_organization.organization_url,
          "organization_logo": new_organization.organization_logo,
          "owner_id": new_organization.owner_id,
          "meta_tag_name": new_organization.meta_tag_name,
          "meta_tag_content": new_organization.meta_tag_name,
          "id": new_organization.id,
          "created_at": new_organization.created_at,
          "updated_at": new_organization.updated_at,
          "owner":new_organization.owner
          }
      return {
          "message": "Organization created successfully",
          "success": True,
          "organization_details": new_organization
          }
  except requests.exceptions.RequestException as e:
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail="Internal Server Error"
          )