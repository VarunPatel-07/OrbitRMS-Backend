import base64
import hashlib
import secrets
from io import BytesIO
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session


class TwitterService:
    def __init__(self, consumer_key: str, consumer_secret: str, callback_uri: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_uri = callback_uri

        self.api_url = "https://api.twitter.com/2"
        self.auth_url = "https://twitter.com/i/oauth2/authorize"
        self.token_url = "https://api.twitter.com/2/oauth2/token"
        self.upload_media_url = "https://upload.twitter.com/1.1/media/upload.json"
        self.delete_tweet_url = "https://api.twitter.com/2/tweets"

        self.scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]

        self.code_verifier = secrets.token_urlsafe(100)[:128]
        self.code_challenge = self._generate_challenge(self.code_verifier)

    def _generate_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    #
    # ?  The Function To Get The Auth Url
    #
    def get_auth_url(self, state: Optional[str] = None) -> str:
        twitter = OAuth2Session(
            client_id=self.consumer_key,
            redirect_uri=self.callback_uri,
            scope=self.scopes,
            state=state,
        )
        authorization_url = twitter.authorization_url(
            self.auth_url,
            code_challenge=self.code_challenge,
            code_challenge_method="S256",
        )

        return authorization_url[0]

    #
    # ?  Now We Are Verifying And Getting The Auth Token
    #
    def fetch_token(self, authorization_response: str):
        twitter_oauth = OAuth2Session(
            client_id=self.consumer_key,
            redirect_uri=self.callback_uri,
            scope=self.scopes,
        )
        token = twitter_oauth.fetch_token(
            token_url=self.token_url,
            authorization_response=authorization_response,
            client_secret=self.consumer_secret,
            code_verifier=self.code_verifier,
        )
        return token

    def refresh_access_token(self, refresh_token: str) -> dict:
        

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.consumer_key,
        }

        response = requests.post(
            self.token_url,
            headers=headers,
            data=data,
            auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret),
        )
        response.raise_for_status()
        return response.json()

    def post_tweet(self, access_token: str, refresh_token: str, text: str, media_ids: Optional[list] = None) -> dict:

        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            url = f"{self.api_url}/tweets"
            payload = {"text": text}

            if media_ids:
                payload["media"] = {"media_ids": media_ids}

            response = requests.post(url=url, headers=headers, json=payload)

            if response.status_code == 403:
                return {
                    "error": True,
                    "status": 403,
                    "details": response.json(),
                    "message": "Forbidden – check app permissions, scopes, or media ownership.",
                }

            response.raise_for_status()

            return {
                "data": response.json(),
                "auth_data": {},
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                new_tokens = self.refresh_access_token(refresh_token)
                
                new_access_token = new_tokens.get("access_token")
                headers = {
                    "Authorization": f"Bearer {new_access_token}",
                    "Content-Type": "application/json",
                }

                url = f"{self.api_url}/tweets"
                payload = {"text": text}

                if media_ids:
                    payload["media"] = {"media_ids": media_ids}

                response = requests.post(url=url, headers=headers, json=payload)

                response.raise_for_status()

                return {
                    "data": response.json(),
                    "auth_data": {
                        "access_token": new_access_token,
                        "refresh_token": new_tokens.get("refresh_token"),
                        "expires_in": new_tokens.get("expires_in"),
                    },
                }
            return str(e)

    def upload_media(self, access_token: str, refresh_token: str, file_bytes: bytes) -> str:
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            files = {"media": ("image.jpg", BytesIO(file_bytes), "image/jpeg")}

            data = {"media_category": "tweet_image"}

            response = requests.post(self.upload_media_url, headers=headers, files=files, data=data)

            response.raise_for_status()

            return response.json().get("media_id_string")

        except requests.exceptions.HTTPError as e:

            if e.response.status_code == 401:  # Unauthorized - token might be expired
                # Refresh the token and retry
                new_tokens = self.refresh_access_token(refresh_token)
                new_access_token = new_tokens["access_token"]

                # Update the token in your database
                # db.query(...).update({...})

                headers = {"Authorization": f"Bearer {new_access_token}"}

                files = {"media": ("image.jpg", BytesIO(file_bytes), "image/jpeg")}

                data = {"media_category": "tweet_image"}
                response = requests.post(self.upload_media_url, headers=headers, files=files)

                response.raise_for_status()

                return response.json().get("media_id_string")
            else:
                raise e

    def delete_tweet(self, access_token: str, refresh_token: str, tweet_id: str) -> dict:
        try:
            url = f"{self.delete_tweet_url}/{tweet_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.delete(url=url, headers=headers)

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Tweet Deleted Successfully",
                    "error": "",
                    "status_code": response.status_code,
                }
            else:
                return {
                    "success": False,
                    "message": "Some Thing Went Wrong",
                    "error": response.text,
                    "status_code": response.status_code,
                }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:

                new_token = self.refresh_access_token(refresh_token=refresh_token)
                new_access_token = new_token["access_token"]
                url = f"{self.delete_tweet_url}/{tweet_id}"

                headers = {
                    "Authorization": f"Bearer {new_access_token}",
                    "Content-Type": "application/json",
                }

                response = requests.delete(url=url, headers=headers)

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Tweet Deleted Successfully",
                        "error": "",
                        "status_code": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "message": "Some Thing Went Wrong",
                        "error": response.text,
                        "status_code": response.status_code,
                    }
