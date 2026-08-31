import asyncio

import cloudinary
from fastapi import HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from config.EnvConfig import EnvConfig
from routes.clientInquires.submitInquiry.crude import (
    get_inquiry_submission_context,
    save_inquiry_send_mail,
    verify_form_schema_service,
)
from routes.clientInquires.submitInquiry.turnstile_client import verify_turnstile_token
from routes.clientInquires.submitInquiry.utils import (
    normalize_allowed_domains,
    parse_inquiry_payload,
    validate_request_origin,
)
from utils.helper.encryption_helper import decrypt_data_service


cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)


async def upload_single_file(file: UploadFile):
    file_bytes = await file.read()

    # An empty browser placeholder must never be sent to Cloudinary.
    if not file_bytes:
        return None

    result = await run_in_threadpool(
        cloudinary.uploader.upload,
        file_bytes,
        resource_type="image",
    )

    return result["secure_url"]


async def submit_inquiry_service_function(request, db, background_task, api_key, api_secret, form_id, turnstile_token):

    query_payload = await parse_inquiry_payload(request=request)

    submission_context = await get_inquiry_submission_context(
        db=db,
        api_key=api_key,
        api_secret=api_secret,
        form_id=form_id,
    )

    if not submission_context.get("success"):
        raise HTTPException(
            status_code=submission_context.get("status_code"),
            detail={
                "message": submission_context.get("message"),
                "success": submission_context.get("success"),
            },
        )

    context_data = submission_context.get("data")
    client_inquiry = context_data.get("client_inquiry")
    organization = context_data.get("organization")
    form_schema = context_data.get("form_schema")

    allowed_domains = normalize_allowed_domains(form_schema.allowed_domains)
    validate_request_origin(request, allowed_domains=allowed_domains)

    try:
        decrypted_secret_key = decrypt_data_service(form_schema.turnstile_secret_key)

        if isinstance(decrypted_secret_key, bytes):
            decrypted_secret_key = decrypted_secret_key.decode("utf-8")

        decrypted_secret_key = decrypted_secret_key.strip().strip('"').strip("'")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": "Unable to decrypt Turnstile secret key.", "error": str(e)},
        )

    cloudflare_payload = {
        "secret": decrypted_secret_key,
        "response": turnstile_token,
        "remoteip": request.client.host if request.client else None,
    }

    try:
        cloudflare_result = await verify_turnstile_token(cloudflare_payload)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "success": False,
                "message": "Invalid response from Turnstile verification service.",
            },
        )

    if not cloudflare_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Turnstile verification failed. Please make sure the required domain is added in Cloudflare allowed domains.",
                "error_codes": cloudflare_result,
            },
        )

    cloudflare_allowed_domains = normalize_allowed_domains(cloudflare_result.get("hostname"))
    validate_request_origin(request, allowed_domains=cloudflare_allowed_domains)

    verify_form_schema = await verify_form_schema_service(
        query_payload=query_payload,
        form_fields=form_schema.inquiry_form_fields,
    )

    if not verify_form_schema.get("success"):
        raise HTTPException(
            status_code=verify_form_schema.get("status_code"),
            detail={
                "message": verify_form_schema.get("message"),
                "success": verify_form_schema.get("success"),
            },
        )

    form_data = verify_form_schema.get("data")

    inquiry_data = {}

    for field in form_data:
        field_name = field["field_name"]
        field_type = field["type"]

        value = query_payload.get(field_name)

        if field_type == "file":
            files_value = value if isinstance(value, list) else [value]
            files_value = [file for file in files_value if file is not None]
            uploaded_files = await asyncio.gather(*(upload_single_file(file) for file in files_value))

            inquiry_data[field_name] = [url for url in uploaded_files if url]

        else:

            inquiry_data[field_name] = value

    client_inquiry_data = await save_inquiry_send_mail(
        db=db,
        client_inquire_id=client_inquiry.id,
        background_task=background_task,
        organization_name=organization.general_info.organization_name,
        portal_slug=organization.general_info.portal_slug,
        organization_profile_picture=organization.general_info.organization_profile_picture,
        form_schema=form_schema,
        inquiry_data=inquiry_data,
        query_payload=inquiry_data,
    )

    return client_inquiry_data
