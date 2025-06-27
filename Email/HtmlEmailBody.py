import os

from dotenv import load_dotenv

from PydanticModels.HelperPydanticModel import WelcomeEmployeeMailModel

load_dotenv(override=True)

INSTAGRAM_LINK = os.getenv("INSTAGRAM_LINK").strip()
FACEBOOK_LINK = os.getenv("FACEBOOK_LINK").strip()
LINKEDIN_LINK = os.getenv("LINKEDIN_LINK").strip()


def VerifyEmailHtmlBody(url: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "email-verification.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (html_content.replace("{verification_link}", url))
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )
    return html_content


def CreatePasswordHtmlBody(url: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "create-password.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (html_content.replace("{create_password_link}", url))
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )
    return html_content


def WelcomeMailForNewlyAddedEmployee(data: WelcomeEmployeeMailModel):

    ORBIT_CONTACT_EMAIL = os.getenv("ORBIT_CONTACT_EMAIL", "").strip()
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "welcome-new-user-mail.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (
            html_content.replace("{user_name}", data.user_name)
            .replace("{organization_name}", data.organization_name)
            .replace("{create_password_link}", data.create_password_link)
        )
        .replace("{orbit_contact_emil}", ORBIT_CONTACT_EMAIL)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )

    return html_content


def NewClientInquiryAccruedMail(url: str, organization_name: str):
    ORBIT_CONTACT_EMAIL = os.getenv("ORBIT_CONTACT_EMAIL", "").strip()

    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "new-client-inquiry-mail.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (
            html_content.replace("{create_password_link}", url).replace(
                "{organization_name}", organization_name
            )
        )
        .replace("{orbit_contact_emil}", ORBIT_CONTACT_EMAIL)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )

    return html_content
