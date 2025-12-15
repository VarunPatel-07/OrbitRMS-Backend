from typing import List, Optional

from fastapi import File, UploadFile
from pydantic import BaseModel


class SocialMediaPostBackgroundTaskData(BaseModel):
    caption: str
    uploaded_file_url: List[str]


class PostPublishRecords(BaseModel):
    platform: str
    post_id: str
