from fastapi import status

MAX_RESET_ATTEMPTS = 4
RESET_TTL_SECONDS = 300
RESEND_OTP_AVAILABLE_AT_DEFAULT_TIME = 150


SERVER_ERROR_STATUS_CODE = [
    status.HTTP_500_INTERNAL_SERVER_ERROR,
    status.HTTP_501_NOT_IMPLEMENTED,
    status.HTTP_502_BAD_GATEWAY,
    status.HTTP_503_SERVICE_UNAVAILABLE,
    status.HTTP_504_GATEWAY_TIMEOUT,
    status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED,
    status.HTTP_506_VARIANT_ALSO_NEGOTIATES,
    status.HTTP_507_INSUFFICIENT_STORAGE,
    status.HTTP_508_LOOP_DETECTED,
    status.HTTP_510_NOT_EXTENDED,
    status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED,
]

PRODUCTION_ENVIRONMENT = "PRODUCTION"
SENTRY_TRACE_SAMPLE_RATE = 1.0
SENTRY_SEND_DEFAULT_PII = False


class SUCCESS:
    FALSE = False
    TRUE = True


USER_FRIENDLY_ERRORS = {
    # ======================================================
    # FACEBOOK
    # ======================================================
    "fb_auth_denied": {
        "title": "Facebook connection was not completed",
        "message": "The Facebook connection process was cancelled before it could be completed. To connect your Facebook account, we need permission to access your Pages. Please restart the connection process and make sure to allow all requested permissions.",
        "action": "Connect Facebook",
    },
    "fb_token_exchange_failed": {
        "title": "Unable to complete Facebook connection",
        "message": "We were unable to complete the connection with Facebook at this time. This can happen due to a temporary issue with Facebook’s services or a network interruption. Your account has not been affected. Please wait a moment and try connecting Facebook again.",
        "action": "Try again",
    },
    "fb_no_pages_found": {
        "title": "No Facebook Pages could be found",
        "message": "We successfully connected to Facebook, but couldn’t find any Facebook Pages linked to your account. To continue, make sure you are an admin or editor of at least one Facebook Page. Once confirmed, return here and try connecting again.",
        "action": "Check Facebook Pages",
    },
    "fb_permission_missing": {
        "title": "Additional Facebook permissions are required",
        "message": "The Facebook account was connected, but some required permissions were not granted. These permissions are necessary for managing and publishing content to your Pages. Please reconnect Facebook and allow all requested permissions to continue.",
        "action": "Reconnect Facebook",
    },
    "fb_unexpected": {
        "title": "Facebook connection encountered an issue",
        "message": "Something interrupted the Facebook connection process before it could be completed. This does not indicate a problem with your account. Please try connecting Facebook again, and contact support if the issue continues.",
        "action": "Retry",
    },
    # ======================================================
    # TWITTER (X)
    # ======================================================
    "tw_auth_denied": {
        "title": "Twitter connection was not completed",
        "message": "The Twitter connection process was cancelled before it could be completed. To connect your Twitter account, we need permission to access your profile. Please start the connection process again and allow the requested permissions.",
        "action": "Connect Twitter",
    },
    "tw_token_exchange_failed": {
        "title": "Unable to complete Twitter connection",
        "message": "We were unable to complete the connection with Twitter at this time. This may be due to a temporary issue with Twitter or a network interruption. No changes were made to your account. Please wait a moment and try again.",
        "action": "Try again",
    },
    "tw_account_deactivated": {
        "title": "Your account is currently unavailable",
        "message": "We’re unable to continue because your account appears to be deactivated or restricted. To proceed, please contact support or reactivate your account. Once your account is active, you can reconnect Twitter.",
        "action": "Contact support",
    },
    "tw_org_deactivated": {
        "title": "Organization access is currently restricted",
        "message": "The organization linked to your account is currently inactive. This prevents us from connecting social media accounts at the moment. Please contact your organization administrator to resolve this and try again later.",
        "action": "Contact administrator",
    },
    "tw_permission_missing": {
        "title": "Additional Twitter permissions are required",
        "message": "The Twitter account was connected, but some required permissions were not granted. These permissions are needed to post content and manage your account. Please reconnect Twitter and allow all requested permissions to continue.",
        "action": "Reconnect Twitter",
    },
    "tw_unexpected": {
        "title": "Twitter connection encountered an issue",
        "message": "An unexpected interruption occurred while connecting your Twitter account. This does not affect your account or existing data. Please try connecting Twitter again in a moment.",
        "action": "Retry",
    },
    # ======================================================
    # LINKEDIN
    # ======================================================
    "li_auth_denied": {
        "title": "LinkedIn connection was not completed",
        "message": "The LinkedIn connection process was cancelled before it could be completed. To connect your LinkedIn account or Page, we need permission to access your profile and Pages. Please start the connection process again and allow all requested permissions.",
        "action": "Connect LinkedIn",
    },
    "li_token_exchange_failed": {
        "title": "Unable to complete LinkedIn connection",
        "message": "We were unable to complete the connection with LinkedIn at this time. This can happen due to a temporary issue with LinkedIn’s services or a network interruption. Please wait a moment and try connecting LinkedIn again.",
        "action": "Try again",
    },
    "li_no_pages_found": {
        "title": "No LinkedIn Pages could be found",
        "message": "We successfully connected to LinkedIn, but couldn’t find any LinkedIn Pages linked to your account. To continue, make sure you are an admin of at least one LinkedIn Page. Once confirmed, return here and try connecting LinkedIn again.",
        "action": "Check LinkedIn Pages",
    },
    "li_permission_missing": {
        "title": "Additional LinkedIn permissions are required",
        "message": "The LinkedIn account was connected, but some required permissions were not granted. These permissions are necessary for managing and publishing content on your behalf. Please reconnect LinkedIn and allow all requested permissions to continue.",
        "action": "Reconnect LinkedIn",
    },
    "li_unexpected": {
        "title": "LinkedIn connection encountered an issue",
        "message": "An unexpected interruption occurred while connecting your LinkedIn account. This does not indicate a problem with your account. Please try connecting LinkedIn again, and contact support if the issue persists.",
        "action": "Retry",
    },
}
