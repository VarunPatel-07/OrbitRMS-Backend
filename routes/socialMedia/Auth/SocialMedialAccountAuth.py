import base64
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import quote, unquote

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from constants.constant import USER_FRIENDLY_ERRORS
from database.Database import db_dependencies
from middleware.RateLimiting import limiter
from models.sql import Models
from utils.helper.helper import redirect_with_error

from ..Services.FacebookService import FacebookService
from ..Services.TwitterService import TwitterService
from ..SocialMediaModuleHelper.UserValidatorFunction import UserValidatorFunction

# Set up logging
logger = logging.getLogger(__name__)

SocialAccountAuth = APIRouter(prefix="/app/v1/social/media/accounts/authenticate", tags=["accounts"])


facebook_service = FacebookService(
    app_id=EnvConfig.META_APP_ID,
    app_secret=EnvConfig.META_APP_SECRET,
    redirect_uri=f"{EnvConfig.BACKEND_BASE_URL}/social/media/accounts/authenticate/facebook/callback",
)

twitter_service = TwitterService(
    consumer_key=EnvConfig.TWITTER_CONSUMER_KEY,
    consumer_secret=EnvConfig.TWITTER_CONSUMER_SECRETE,
    callback_uri=f"{EnvConfig.BACKEND_BASE_URL}/social/media/accounts/authenticate/twitter/callback",
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

            return redirect_with_error(organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.fb_auth_denied)

        # Exchange code for token
        try:
            token_data = facebook_service.exchange_code_for_token(code)
            if not token_data.get("access_token"):
                raise ValueError("No access token in response")
        except Exception as e:
            return redirect_with_error(
                organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.fb_token_exchange_failed
            )

        access_token = token_data["access_token"]

        # Get long-lived token
        try:
            long_lived_token = facebook_service.get_long_lived_token(access_token)
            long_access_token = long_lived_token.get("access_token")
            expires_in = long_lived_token.get("expires_in", 0)

            if not long_access_token:
                raise ValueError("No long-lived access token received")

        except Exception as e:
            return redirect_with_error(
                organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.fb_token_exchange_failed
            )
            # raise HTTPException(status_code=400, detail="Failed to obtain long-lived token")

        expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

        # Get user pages
        try:
            pages = facebook_service.get_user_pages(long_access_token)

            if not pages:
                raise ValueError("No pages found for this user")
        except Exception as e:
            logger.error(f"Failed to get user pages: {str(e)}")
            return redirect_with_error(organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.fb_no_pages_found)
            # raise HTTPException(
            #     status_code=400,
            #     detail={"message": "Failed to retrieve Facebook pages", "error": str(e)},
            # )

        # Process pages (here we'll just take the first one)
        for page in pages:

            page_id = page.get("id")
            page_name = page.get("name")
            page_access_token = page.get("access_token")

            if not all([page_id, page_name, page_access_token]):
                return redirect_with_error(
                    organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.fb_no_pages_found
                )
                # raise HTTPException(status_code=400, detail="Incomplete page data received")

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

        frontend_url = f"{EnvConfig.FRONTEND_URL}/{organization.general_info.portal_slug}/social-media/"
        clean_url = frontend_url.split("#")[0]
        return RedirectResponse(url=clean_url)

    except HTTPException:
        raise  # Re-raise already handled exceptions
    except Exception as e:
        logger.error(f"Unexpected error in Facebook callback: {str(e)}")
        return redirect_with_error(organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.fb_unexpected)
        # raise HTTPException(
        #     status_code=500,
        #     detail={
        #         "message": "An unexpected error occurred during Facebook authentication",
        #         "error": str(e),
        #     },
        # )


@SocialAccountAuth.get("/login/twitter", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def Login_With_The_Twitter(
    request: Request,
    db: db_dependencies,
    org_id: str = Query(..., alias="org-id"),
    token: str = Query(..., alias="token"),
):

    user = UserValidatorFunction(request=request, db=db, token=token)

    organization = db.query(Models.Organization).filter(Models.Organization.id == org_id).first()

    if not organization:
        return RedirectResponse(url=f"{EnvConfig.FRONTEND_URL}/auth/sign-in")

    state_data = {"org_id": org_id, "user_id": user.id}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    auth_url = twitter_service.get_auth_url(state)

    return RedirectResponse(url=auth_url)


@SocialAccountAuth.get("/twitter/callback", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def twitter_callback_handler(
    request: Request,
    db: db_dependencies,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None),
    error_reason: str = Query(None),
    error_description: str = Query(None),
):
    try:
        # Parse state (org_id + token)
        try:
            state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            org_id = state_data["org_id"]
            user_id = state_data["user_id"]
        except (json.JSONDecodeError, KeyError):
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        user = db.query(Models.User).filter(Models.User.id == user_id).first()

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ("Account is deactivated. Access denied." if user.account_status else "User Not Found"),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        organization = (
            db.query(Models.Organization)
            .options(joinedload(Models.Organization.general_info))
            .filter(Models.Organization.id == org_id)
            .first()
        )

        if not organization:
            return RedirectResponse(url=f"{EnvConfig.FRONTEND_URL}/auth/sign-in")

        if error:
            return redirect_with_error(organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.tw_auth_denied)
            # raise HTTPException(
            #     status_code=400,
            #     detail=f"Twitter authentication failed: {error_description}",
            # )

        # Exchange code for token
        full_url = str(request.url)  # includes ?code=...&state=...
        token_data = twitter_service.fetch_token(full_url)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        if not access_token:
            return redirect_with_error(
                organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.tw_token_exchange_failed
            )
        # raise HTTPException(status_code=400, detail="No access token received from Twitter")

        expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

        # Save to DB (for now, just as Twitter account)
        existing_account = (
            db.query(Models.SocialMediaAccount)
            .filter(
                and_(
                    Models.SocialMediaAccount.organization_id == org_id,
                    Models.SocialMediaAccount.platform == "twitter",
                )
            )
            .first()
        )

        if existing_account:
            existing_account.access_token = access_token
            existing_account.expires_at = expires_at
            existing_account.extra_data = {"refresh_token": refresh_token}
            existing_account.refresh_token = refresh_token
        else:
            db.add(
                Models.SocialMediaAccount(
                    account_name="twitter",  # could later fetch actual username via
                    access_token=access_token,
                    platform="twitter",
                    expires_at=expires_at,
                    extra_data={"refresh_token": refresh_token},
                    organization_id=org_id,
                    refresh_token=refresh_token,
                )
            )

        db.commit()

        frontend_url = f"{EnvConfig.FRONTEND_URL}/{organization.general_info.portal_slug}/social-media/"
        clean_url = frontend_url.split("#")[0]
        return RedirectResponse(url=clean_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Twitter callback: {str(e)}")
        return redirect_with_error(organization.general_info.portal_slug, USER_FRIENDLY_ERRORS.tw_unexpected)
        # raise HTTPException(
        #     status_code=500,
        #     detail={"message": "Unexpected error during Twitter authentication", "error": str(e)},
        # )
