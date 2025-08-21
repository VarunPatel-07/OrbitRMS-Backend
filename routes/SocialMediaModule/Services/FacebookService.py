import requests
from datetime import datetime
from typing import Optional, List, Dict
import facebook
import logging
import json
import time

logger = logging.getLogger(__name__)


class FacebookService:
    def __init__(self, app_id: str, app_secret: str, redirect_uri: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
        self.api_version = "v23.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Generate Facebook OAuth URL with required permissions"""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state or "",
            "scope": ",".join(
                [
                    "business_management",
                    "pages_show_list",
                    "pages_read_engagement",
                    "pages_manage_posts",
                    "instagram_basic",
                    "instagram_content_publish",
                    "public_profile",
                ]
            ),
            "response_type": "code",
        }
        return f"https://www.facebook.com/{self.api_version}/dialog/oauth?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for short-lived access token"""
        url = f"{self.base_url}/oauth/access_token"
        params = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": self.redirect_uri,
            "code": code,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_long_lived_token(self, short_lived_token: str) -> dict:
        """Convert short-lived token to long-lived token"""
        url = f"{self.base_url}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def verify_token(self, access_token: str) -> dict:
        """Verify token validity and get metadata"""
        url = f"{self.base_url}/debug_token"
        params = {"input_token": access_token, "access_token": f"{self.app_id}|{self.app_secret}"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_business_accounts(self, access_token: str) -> List[Dict]:
        """Get business accounts associated with the user"""
        url = f"{self.base_url}/me/businesses"
        params = {"access_token": access_token, "fields": "id,name"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_business_pages(self, business_id: str, access_token: str) -> List[Dict]:
        """Get pages owned by a business account"""
        url = f"{self.base_url}/{business_id}/owned_pages"
        params = {
            "access_token": access_token,
            "fields": "id,name,access_token,instagram_business_account{id,username}",
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_user_pages(self, access_token: str) -> List[Dict]:
        """Get all pages accessible to the user, including business-owned pages"""
        try:
            # Verify token first
            token_info = self.verify_token(access_token)
            if not token_info.get("data", {}).get("is_valid"):
                raise ValueError("Access token is invalid")

            # Check for required permissions
            granted_scopes = token_info.get("data", {}).get("scopes", [])
            required_scopes = {"pages_show_list", "business_management"}
            if not required_scopes.issubset(granted_scopes):
                raise ValueError(f"Missing required permissions. Granted: {granted_scopes}")

            # First try to get directly managed pages
            url = f"{self.base_url}/me/accounts"
            params = {
                "access_token": access_token,
                "fields": "id,name,access_token,instagram_business_account{id,username}",
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            pages = data.get("data", [])

            # If no pages found, check business accounts
            if not pages:
                businesses = self.get_business_accounts(access_token)
                for business in businesses:
                    business_pages = self.get_business_pages(business["id"], access_token)
                    if business_pages:
                        pages.extend(business_pages)
                        break

            if not pages:
                raise ValueError(
                    "No pages found. User may not be an admin of any pages or missing permissions."
                )

            # Enhance page data with Instagram info
            enhanced_pages = []
            for page in pages:
                page_data = {
                    "id": page.get("id"),
                    "name": page.get("name"),
                    "access_token": page.get("access_token"),
                }

                if isinstance(page.get("instagram_business_account"), dict):
                    ig_account = page["instagram_business_account"]
                    page_data["instagram_account"] = {
                        "id": ig_account.get("id"),
                        "username": ig_account.get("username"),
                    }

                enhanced_pages.append(page_data)

            return enhanced_pages

        except requests.exceptions.RequestException as e:
            error_msg = f"Facebook API request failed: {str(e)}"
            if hasattr(e, "response") and e.response:
                error_msg += f" | Response: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def post_to_page(
        self,
        page_id: str,
        access_token: str,
        message: str,
        media_urls: List[str] = None,
        link: Optional[str] = None,
    ) -> dict:
        # First We Will Initialize An Graph
        graph = facebook.GraphAPI(access_token=access_token)

        # Now We Will Check For The Media Urls
        if not media_urls:
            post_args = {
                "message": message,
            }
            if link:
                post_args["link"] = link
            return graph.put_object(page_id, "feed", **post_args)

        if len(media_urls) == 1:

            post_args = {"message": message, "url": media_urls}
            return graph.put_object(page_id, "photos", **post_args)
        else:
            return self._post_multiple_images_to_facebook(
                page_id, access_token, message, media_urls
            )

    def _post_multiple_images_to_facebook(
        self, page_id: str, access_token: str, message: str, media_urls: List[str]
    ) -> dict:

        graph = facebook.GraphAPI(access_token=access_token)

        uploaded_photo_ids = []

        for image_url in media_urls:

            response = graph.put_object(
                parent_object=page_id, connection_name="photos", url=image_url, published=False
            )
            uploaded_photo_ids.append(response["id"])

        attached_media = [{"media_fbid": photo_id} for photo_id in uploaded_photo_ids]

        post_args = {"message": message, "attached_media": json.dumps(attached_media)}

        return graph.put_object(page_id, "feed", **post_args)

    def post_to_instagram(
        self, page_id: str, access_token: str, media_urls: List[str], caption: str
    ) -> dict:
        try:
            # Now First We Will Check For The Length Of The Image
            if len(media_urls) == 1:
                return self._post_single_image_to_instagram(
                    page_id, access_token, media_urls, caption
                )

            else:
                return self._post_carousel_to_instagram(page_id, access_token, media_urls, caption)

        except requests.exceptions.RequestException as e:
            error_msg = str(e)

            if hasattr(e, "response") and e.response is not None:

                try:
                    error_data = e.response.json()
                    error_msg = f"{error_msg}. Response: {json.dumps(error_data)}"
                except:
                    pass
            raise Exception(f"Instagram API error: {error_msg}")

    def _post_single_image_to_instagram(
        self, page_id: str, access_token: str, media_url: str, caption: str
    ) -> dict:

        instagram_base_url = f"{self.base_url}/{page_id}/media"
        params = {"image_url": media_url, "caption": caption, "access_token": access_token}

        response = requests.post(instagram_base_url, params=params)
        response.raise_for_status()

        creation_id = response.json().get("id")

        return self._publish_instagram_media(
            page_id=page_id, access_token=access_token, creation_id=creation_id
        )

        # Now As The Image IS Uploaded We Will Transfer That Image To The Publish Instagram Media

    def _post_carousel_to_instagram(
        self, page_id: str, access_token: str, media_urls: List[str], caption: str
    ) -> dict:
        uploaded_media_ids = []

        instagram_base_url = f"{self.base_url}/{page_id}/media"

        for image_url in media_urls:

            params = {
                "image_url": image_url,
                "is_carousel_item": True,
                "access_token": access_token,
            }

            response = requests.post(instagram_base_url, params=params)
            response.raise_for_status()
            uploaded_media_ids.append(response.json().get("id"))

        time.sleep(2)

        create_carousel_base_url = f"{self.base_url}/{page_id}/media"

        params = {
            "caption": caption,
            "media_type": "CAROUSEL",
            "children": ",".join(uploaded_media_ids),
            "access_token": access_token,
        }

        response = requests.post(create_carousel_base_url, params=params)
        response.raise_for_status()
        carousel_id = response.json().get("id")

        return self._publish_instagram_media(
            page_id=page_id, access_token=access_token, creation_id=carousel_id
        )

    def _publish_instagram_media(self, page_id: str, access_token: str, creation_id):

        insta_publish_url = f"{self.base_url}/{creation_id}"
        status_params = {"fields": "status_code", "access_token": access_token}

        for _ in range(10):
            status_response = requests.get(insta_publish_url, params=status_params)
            status_data = status_response.json()

            if status_data.get("status_code") == "FINISHED":
                break

            time.sleep(3)

        publish_url = f"{self.base_url}/{page_id}/media_publish"
        params = {"creation_id": creation_id, "access_token": access_token}

        response = requests.post(publish_url, params=params)

        response.raise_for_status()
        return response.json()

    def delete_from_page(self, post_id: str, access_token: str) -> dict:
        try:
            graph = facebook.GraphAPI(access_token=access_token)
            try:
                graph.delete_object(post_id)

                return {"success": True, "message": "Post deleted successfully"}
            except facebook.GraphAPIError as e:
                error_msg = str(e)

                if "permission" in error_msg.lower():

                    if "_" in post_id and post_id.split("_")[0] != post_id:

                        photo_id = post_id.split("_")[1]
                        graph.delete_object(photo_id)

                        return {"success": True, "message": "Photo deleted successfully"}

            raise
        except facebook.GraphAPIError as e:
            raise Exception(f"Facebook API error: {str(e)}")

    def get_post_insights(self, post_id: str, access_token: str) -> dict:

        url = f"{self.base_url}/{post_id}/insights"
        params = {
            "metric": "engagement,impressions,reach,reactions,comments,shares",
            "access_token": access_token,
        }

        response = requests.get(url, params=params)

        response.raise_for_status()

        return response.json()
