from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, Query, Request, status

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from middleware.RateLimiting import limiter
from routes.clientInquires.submitInquiry.service import submit_inquiry_service_function
from utils.responseMessages import ERROR_MESSAGE

inquiryPublicRouter = APIRouter(prefix="/public/v1/inquiries", tags=["ClientInquiries"])


#  This is the API for Submitting the API The From this is an public Facing Api
@inquiryPublicRouter.post(path="/submit", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def handel_submit_inquires(
    request: Request,
    db: db_dependencies,
    background_task: BackgroundTasks,
    x_api_key: str = Header(..., alias="X-API-Key"),
    x_api_secret: str = Header(..., alias="X-API-Secret"),
    turnstile_token: str = Header(..., alias="X-Turnstile-Token"),
    form_id: str = Query(..., alias="form_id"),
):
    try:
        return await submit_inquiry_service_function(
            request,
            db,
            background_task,
            api_key=x_api_key,
            api_secret=x_api_secret,
            form_id=form_id,
            turnstile_token=turnstile_token,
        )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.SUBMIT_INQUIRY.ERROR_WHILE_SUBMITTING_INQUIRY,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )
