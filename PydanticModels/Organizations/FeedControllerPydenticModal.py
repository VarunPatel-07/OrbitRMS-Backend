from pydantic import BaseModel


class FeedPostPydanticModel(BaseModel):
    description: str
    isCommentDisabled: bool
    isLikeDisabled: bool


class FeedCommentData(BaseModel):
    comment: str
