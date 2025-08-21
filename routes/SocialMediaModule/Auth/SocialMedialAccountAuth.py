from fastapi import APIRouter, Request, Query, status, HTTPException
from ..SocialMediaModuleHelper.UserValidatorFunction import UserValidatorFunction
from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import joinedload
from Database.Database import db_dependencies
from RateLimiting import limiter
from Config.EnvConfig import EnvConfig
from ..Services.FacebookService import FacebookService
from fastapi.responses import RedirectResponse
from urllib.parse import quote, unquote
from datetime import datetime, timedelta
from SqlModels import Models
import logging
import json

# Set up logging
logger = logging.getLogger(__name__)

SocialAccountAuth = APIRouter(
    prefix="/app/v1/social/media/accounts/authenticate", tags=["accounts"]
)


facebook_service = FacebookService(
    app_id=EnvConfig.META_APP_ID,
    app_secret=EnvConfig.META_APP_SECRET,
    redirect_uri=f"{EnvConfig.BACKEND_BASE_URL}/social/media/accounts/authenticate/facebook/callback",
)


@SocialAccountAuth.get("/login/facebook", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def facebook_auth(
    request: Request,
    db: db_dependencies,
    org_id: str = Query(..., alias="org-id"),
    token: str = Query(..., alias="token"),
):

    UserValidatorFunction(request=request, db=db, token=token)

    organization = db.query(Models.Organization).filter(Models.Organization.id == org_id).first()

    if not organization:
        return RedirectResponse(url=f"{EnvConfig.FRONTEND_URL}/auth/sign-in")

    state_data = {"org_id": org_id, "token": token}

    state = quote(json.dumps(state_data))

    auth_url = facebook_service.get_auth_url(state)
    # return {"auth_url": auth_url}
    return RedirectResponse(url=auth_url)


@SocialAccountAuth.get("/facebook/callback")
async def facebook_callback(
    request: Request,
    db: db_dependencies,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None),
    error_reason: str = Query(None),
    error_description: str = Query(None),
):
    try:

        # UserValidatorFunction(request=request, db=db, token=token)
        try:
            state_data = json.loads(unquote(state))
            org_id = state_data["org_id"]
            token = state_data["token"]

        except (json.JSONDecodeError, KeyError) as e:

            raise HTTPException(status_code=400, detail="Invalid state parameter")

        user = UserValidatorFunction(request=request, db=db, token=token)

        organization = (
            db.query(Models.Organization)
            .options(
                joinedload(Models.Organization.general_info),
            )
            .filter(Models.Organization.id == org_id)
            .first()
        )

        if not organization:
            return RedirectResponse(url=f"{EnvConfig.FRONTEND_URL}/auth/sign-in")

        if error:
            raise HTTPException(
                status_code=400, detail=f"Facebook authentication failed: {error_description}"
            )

        # Exchange code for token
        try:
            token_data = facebook_service.exchange_code_for_token(code)
            if not token_data.get("access_token"):
                raise ValueError("No access token in response")
        except Exception as e:

            raise HTTPException(status_code=400, detail="Failed to exchange code for token")

        access_token = token_data["access_token"]

        # Get long-lived token
        try:
            long_lived_token = facebook_service.get_long_lived_token(access_token)
            long_access_token = long_lived_token.get("access_token")
            expires_in = long_lived_token.get("expires_in", 0)

            if not long_access_token:
                raise ValueError("No long-lived access token received")

        except Exception as e:

            raise HTTPException(status_code=400, detail="Failed to obtain long-lived token")
        print(expires_in)

        expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

        # Get user pages
        try:
            pages = facebook_service.get_user_pages(long_access_token)

            if not pages:
                raise ValueError("No pages found for this user")
        except Exception as e:
            logger.error(f"Failed to get user pages: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail={"message": "Failed to retrieve Facebook pages", "error": str(e)},
            )

        # Process pages (here we'll just take the first one)
        for page in pages:

            page_id = page.get("id")
            page_name = page.get("name")
            page_access_token = page.get("access_token")

            if not all([page_id, page_name, page_access_token]):
                raise HTTPException(status_code=400, detail="Incomplete page data received")

            existing_account = (
                db.query(Models.SocialMediaAccount)
                .filter(
                    and_(
                        Models.SocialMediaAccount.organization_id == org_id,
                        Models.SocialMediaAccount.platform == "facebook",
                        Models.SocialMediaAccount.extra_data["page_id"] == str(page_id),
                    )
                )
                .first()
            )

            if existing_account:
                existing_account.access_token = page_access_token
                existing_account.expires_at = expires_at
                existing_account.extra_data = {
                    "page_id": page_id,
                    "user_access_token": long_access_token,
                }
            else:
                db.add(
                    Models.SocialMediaAccount(
                        account_name=page_name,
                        access_token=page_access_token,
                        platform="facebook",
                        expires_at=expires_at,
                        extra_data={"page_id": page_id, "user_access_token": long_access_token},
                        organization_id=org_id,
                    )
                )

            if "instagram_account" in page and isinstance(page.get("instagram_account"), dict):
                insta_page_id = page.get("instagram_account").get("id")
                insta_page_name = page.get("instagram_account").get("username")

                existing_insta_account = (
                    db.query(Models.SocialMediaAccount)
                    .filter(
                        and_(
                            Models.SocialMediaAccount.organization_id == org_id,
                            Models.SocialMediaAccount.platform == "instagram",
                            Models.SocialMediaAccount.extra_data["page_id"] == str(insta_page_id),
                        )
                    )
                    .first()
                )

                if not existing_insta_account:
                    db.add(
                        Models.SocialMediaAccount(
                            account_name=insta_page_name,
                            access_token=page_access_token,
                            platform="instagram",
                            expires_at=expires_at,
                            extra_data={
                                "page_id": insta_page_id,
                                "user_access_token": long_access_token,
                            },
                            organization_id=org_id,
                        )
                    )
                else:
                    existing_insta_account.access_token = page_access_token
                    existing_insta_account.expires_at = expires_at
                    existing_insta_account.extra_data = {
                        "page_id": insta_page_id,
                        "user_access_token": long_access_token,
                    }

        db.commit()

        frontend_url = (
            f"{EnvConfig.FRONTEND_URL}/{organization.general_info.portal_slug}/social-media/"
        )
        clean_url = frontend_url.split("#")[0]
        return RedirectResponse(url=clean_url)

    except HTTPException:
        raise  # Re-raise already handled exceptions
    except Exception as e:
        logger.error(f"Unexpected error in Facebook callback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during Facebook authentication",
                "error": str(e),
            },
        )
