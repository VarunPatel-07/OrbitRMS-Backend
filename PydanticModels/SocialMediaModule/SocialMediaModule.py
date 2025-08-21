from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, File


class SocialMediaPostBackgroundTaskData(BaseModel):
    caption: str
    uploaded_file_url: List[str]


class PostPublishRecords(BaseModel):
    platform: str
    post_id: str
