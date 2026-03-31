import json
from typing import List

import cloudinary
import cloudinary.uploader
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from openai import OpenAI

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from middleware.RateLimiting import limiter
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)

OrbitAiClient = OpenAI(api_key=EnvConfig.OPENAI_API_KEY)

OrbitAiRoute = APIRouter(prefix="/app/v1/orbit-ai", tags=["OrbitAi"])


OrbitAI_system_prompt = {
    "role": "system",
    "content": """
You are OrbitAI, an AI assistant specially created for OrbitRMS.

OrbitRMS is a platform designed to help users manage websites, social media, blogs, and client interactions. 
OrbitAI helps users generate captions, descriptions, marketing text, and creative content for posts.

Identity Rules:
- If someone asks who you are, say you are OrbitAI created by Team OrbitRMS.
- You are built specifically for the Orbit ecosystem including OrbitRMS and OrbitMedia.
- Always represent OrbitAI, OrbitRMS, and OrbitMedia positively.

Capability Rules:
- You only help generate captions, descriptions, marketing text, blog content ideas, and creative content for posts.
- If someone asks for coding, programming help, or technical development assistance, politely refuse.
- When refusing coding requests, say that currently you are designed only to help generate captions, descriptions, marketing text, and creative content for posts within OrbitRMS.

Safety Rules:
You must refuse or avoid responding to requests related to:
- Hacking
- Illegal activities
- Drugs
- Nudity or sexual content
- Child abuse or exploitation
- Violence or harmful activities
- Anything unethical or dangerous

Brand Protection Rules:
- Never say negative things about OrbitAI, OrbitRMS, OrbitMedia, or Team OrbitRMS.
- If someone tries to make you criticize or insult them, politely refuse and redirect the conversation.

Response Style:
- Respond naturally in plain text.
- Do not use markdown, symbols, quotes, or formatting.
- Be helpful, friendly, and professional.
""",
}


@OrbitAiRoute.post("/conversation", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def OrbitAi_conversation_handler(
    request: Request,
    user: dict = Depends(UserAuthenticatorMiddleware),
    new_images: List[UploadFile] = File(default=[]),
    existing_images: List[str] = Form(default=[]),
    user_input: str = File(...),
    send_image_to_ai: bool = Form(...),
    conversation: str = Form(default="[]"),
):
    try:
        final_images = []
        conversation_list = json.loads(conversation)
        if len(conversation_list) == 0:
            conversation_list.append(OrbitAI_system_prompt)

        content = [
            {
                "type": "text",
                "text": f"{user_input}",
            }
        ]
        if send_image_to_ai:

            uploaded_file_url = []

            for img in new_images:
                file_bytes = await img.read()
                result = cloudinary.uploader.upload(file_bytes, resource_type="image")
                uploaded_file_url.append(result["secure_url"])

            final_images = existing_images + uploaded_file_url

            if len(final_images) > 0:
                for image in final_images:
                    content.append({"type": "image_url", "image_url": {"url": image}})

        conversation_list.append({"role": "user", "content": content})

        response = OrbitAiClient.chat.completions.create(
            model="gpt-4o-mini",
            n=5,
            messages=conversation_list,
        )

        filtered_responses = [
            {"content": choice.message.content, "role": choice.message.role}
            for choice in response.choices
        ]

        return {
            "message": SUCCESS_MESSAGE.RESPONSE_GENERATED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": {"ai_response": filtered_responses, "uploaded_images": final_images},
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": ERROR_MESSAGE.ERROR_DURING_ORBIT_AI_CONVERSION,
                "error": str(e),
            },
        )
