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
from constants.constant import SUCCESS
from config.EnvConfig import EnvConfig
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from middleware.RateLimiting import limiter

cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)

OrbitAiClient = OpenAI(api_key=EnvConfig.OPENAI_API_KEY)

OrbitAiRoute = APIRouter(prefix="/app/v1/orbit-ai", tags=["OrbitAi"])


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
        content = [
            {
                "type": "text",
                "text": f"{user_input}\n\nReturn only plain text with no Markdown, symbols, or formatting. Do not include quotes or asterisks. Respond naturally.",
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
            "message": "response generated successfully",
            "success": SUCCESS.TRUE,
            "data": {"ai_response": filtered_responses, "uploaded_images": final_images},
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An error occurred during The OrbitAi conversations",
                "error": str(e),
            },
        )
