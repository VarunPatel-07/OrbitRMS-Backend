import json
import math
import os
from typing import Optional
from urllib.parse import unquote

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from Config.EnvConfig import EnvConfig
from Database.Database import db_dependencies
from Email.HtmlEmailBody import NewClientInquiryAccruedMail
from Helper.emailSender import EmailSchema, email_sender_function
from Helper.helper import (
    filter_fields,
    is_valid_type,
    model_to_filtered_dict,
    validate_field,
)
from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from Middleware.verifyToken import verify_token
from RateLimiting import limiter
from SqlModels import Models

from .ClientInquiresQueryFilter import apply_client_inquiry_query_filter

load_dotenv(override=True)
API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING

FRONTEND_URL = EnvConfig.FRONTEND_URL.strip()

clientInquires = APIRouter(prefix="/app/v1/client-inquires", tags=["clientInquires"])


#
# ? Fetch All The Client Inquiry Data That Have Been Submitted
#
@clientInquires.get(path="/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def Fetch_Client_Inquires(
    request: Request,
    db: db_dependencies,
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
    filter: Optional[str] = Query(None),
    form_id: str = Query(..., alias="form_id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        client_inquires = (
            db.query(Models.ClientInquires)
            .filter(Models.ClientInquires.organization_id == user.organization_id)
            .first()
        )

        filter_data = ""
        if filter:
            decoded = unquote(filter)
            filter_data = json.loads(decoded)

        if not client_inquires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )

        query_data = db.query(Models.ClientInquiresData).filter(
            and_(
                Models.ClientInquiresData.client_inquire_id == client_inquires.id,
                Models.ClientInquiresData.form_id == form_id,
            )
        )
        total_data = 0

        page = page if page else 1
        limit = limit if limit else 10

        start = (page - 1) * limit
        end = start + limit

        if filter_data:
            query_data = apply_client_inquiry_query_filter(query_data, filter_data)
            total_data = query_data.count()
            query_data = query_data.offset(start).limit(end)

        else:
            total_data = query_data.count()

            query_data = query_data.offset(start).limit(end)

        return {
            "message": "Client Inquiry Fetched Successfully",
            "success": True,
            "data": [
                {
                    **filter_fields(_data.data, ["-client_inquire_id", "-id"]),
                    "client_inquire_id": _data.client_inquire_id,
                    "id": _data.id,
                    "form_id": _data.form_id,
                    "form_name": _data.form_name,
                }
                for _data in query_data
            ],
            "metadata": {
                "total_data": total_data,
                "total_pages": math.ceil(total_data / limit),
                "current_page": page,
                "record_per_page": limit,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable To Enable Api Right Now",
                "success": False,
                "error": str(e),
            },
        )


@clientInquires.delete("/delete-inquire")
@limiter.limit(API_RATE_LIMITING)
async def DeleteClientInquire(
    request: Request,
    db: db_dependencies,
    id: str = Query(..., alias="id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        client_inquiry = (
            db.query(Models.ClientInquiresData).filter(Models.ClientInquiresData.id == id).first()
        )
        if not client_inquiry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Client Inquiry Not Found", "success": False},
            )
        db.delete(client_inquiry)
        db.commit()

        return {"message": "Inquiry Deleted Successfully", "success": True}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable Delete Inquiry Right Now",
                "success": False,
                "error": str(e),
            },
        )
