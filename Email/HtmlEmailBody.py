import os

from dotenv import load_dotenv

from Config.EnvConfig import EnvConfig
from PydanticModels.HelperPydanticModel import (
    CreatePasswordPydanticBody,
    NewClientInquiryMailPydanticBody,
    VerifyEmailPydanticBody,
    WelcomeEmployeeMailModel,
    NewOrganizationCreatedSuccessFully,
)

load_dotenv(override=True)

INSTAGRAM_LINK = EnvConfig.INSTAGRAM_LINK.strip()
FACEBOOK_LINK = EnvConfig.FACEBOOK_LINK.strip()
LINKEDIN_LINK = EnvConfig.LINKEDIN_LINK.strip()
ORBIT_CONTACT_EMAIL = EnvConfig.ORBIT_CONTACT_EMAIL.strip()


def VerifyEmailHtmlBody(data: VerifyEmailPydanticBody):

    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "email-verification.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (
            html_content.replace("{confirm_my_email}", data.confirm_my_email).replace(
                "{organization_name}", data.organization_name
            )
        )
        .replace("{orbit_contact_emil}", ORBIT_CONTACT_EMAIL)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )
    return html_content


def CreatePasswordHtmlBody(data: CreatePasswordPydanticBody):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "create-password.html")
    with open(path, "r") as file:
        html_content = file.read()

    html_content = (
        (html_content.replace("{create_password_link}", data.create_password_link))
        .replace("{user_name}", data.user_name)
        .replace("{organization_name}", data.organization_name)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )
    return html_content


def ResetPasswordHtmlBody(url: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "reset-password.html")
    with open(path, "r") as file:
        html_content = file.read()

        print(url)
    html_content = (
        (html_content.replace("{create_password_link}", url))
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )
    return html_content


def ResetPasswordInstructionHtmlBody(data: NewClientInquiryMailPydanticBody):

    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "rest-password-instruction.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (
            html_content.replace("{user_name}", data.user_name)
            .replace("{organization_name}", data.organization_name)
            .replace("{reset_password_link}", data.reset_password_link)
        )
        .replace("{orbit_contact_emil}", ORBIT_CONTACT_EMAIL)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )

    return html_content


def WelcomeMailForNewlyAddedEmployee(data: WelcomeEmployeeMailModel):

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


def WelcomeMailNewOrganization(data: NewOrganizationCreatedSuccessFully):

    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "welcome-new-org.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (
            html_content.replace("{user_name}", data.user_name)
            .replace("{organization_name}", data.organization_name)
            .replace("{organization_dashboard_link}", data.organization_dashboard_link)
        )
        .replace("{orbit_contact_emil}", ORBIT_CONTACT_EMAIL)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )

    return html_content


def render_value(value):
    """Render dict, list, or primitive values into email-friendly HTML."""
    if value is None or value == "":
        return "-"

    # list of primitives
    if isinstance(value, list) and all(not isinstance(v, (dict, list)) for v in value):
        return ", ".join(str(v) for v in value)

    # list of dicts
    if isinstance(value, list) and all(isinstance(v, dict) for v in value):
        inner = []
        for obj in value:
            inner.append("<ul style='margin:0; padding-left:16px;'>")
            for k, v in obj.items():
                inner.append(f"<li><strong>{k}:</strong> {render_value(v)}</li>")
            inner.append("</ul>")
        return "".join(inner)

    # dict
    if isinstance(value, dict):
        inner = [f"<div><strong>{k}:</strong> {render_value(v)}</div>" for k, v in value.items()]
        return "".join(inner)

    # everything else (str, int, bool)
    return str(value)


def format_client_details(client_details: dict) -> str:

    total = len(client_details)
    rows = []
    for idx, (key, value) in enumerate(client_details.items()):
        is_first = idx == 0
        is_last = idx == (total - 1)

        # base styles
        label_style = (
            "padding:12px 16px; width:20%; background:#f9f9f9; "
            "font-weight:bold; text-transform:capitalize; vertical-align:top;"
            "font-family: Montserrat, Trebuchet MS, Lucida Grande, Lucida Sans Unicode,Lucida Sans, Tahoma, sans-serif;"
        )
        value_style = (
            "padding:12px 16px; width:80%; background:#ffffff; color:#555; "
            "vertical-align:top; word-break:break-word; overflow-wrap:anywhere;"
            "font-family: Montserrat, Trebuchet MS, Lucida Grande, Lucida Sans Unicode,Lucida Sans, Tahoma, sans-serif;"
        )

        # separator between rows (only for non-first rows)
        if not is_first:
            sep = "border-top:1px solid rgba(0,0,0,0.06);"
            label_style += sep
            value_style += sep

        # corner radii adjustments
        if total == 1:
            label_style += " border-radius:8px 0 0 8px;"
            value_style += " border-radius:0 8px 8px 0;"
        else:
            if is_first:
                label_style += " border-top-left-radius:8px;"
                value_style += " border-top-right-radius:8px;"
            if is_last:
                label_style += " border-bottom-left-radius:8px;"
                value_style += " border-bottom-right-radius:8px;"

        rows.append(
            f"""
            <tr>
              <td style="{label_style}">{key}</td>
              <td style="{value_style}">{render_value(value)}</td>
            </tr>
            """
        )

    inner_rows_html = "\n".join(rows)

    # outer wrapper with card border + radius and MSO fallback
    html = f"""
<table border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%; border-collapse:collapse; font-size:14px; color:#333;" width="100%">
  <tr>
    <td style="padding:30px 16px; font-family: Montserrat, Trebuchet MS, Lucida Grande, Lucida Sans Unicode,
                                        Lucida Sans, Tahoma, sans-serif; font-size:15px; line-height:1.5; text-align:start; color:#555555;">
      <h3 style="margin:0 0 15px; color:#222;">📝 Inquiry Details</h3>

      <!-- card wrapper -->
      <table role="presentation" width="100%" style="border-collapse:separate; border-spacing:0;">
        <tr>
          <td style="background:#ffffff; border:1px solid rgba(0,0,0,0.1); border-radius:8px; padding:0;">

            <!--[if mso]>
            <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" style="height: auto; v-text-anchor:top; width:100%;" arcsize="10%" strokecolor="#e6e6e6" fillcolor="#ffffff">
              <v:textbox inset="0,0,0,0">
            <![endif]-->

            <!-- inner rows -->
            <table role="presentation" width="100%" style="border-collapse:collapse; width:100%;">
              {inner_rows_html}
            </table>

            <!--[if mso]>
              </v:textbox>
            </v:roundrect>
            <![endif]-->

          </td>
        </tr>
      </table>

    </td>
  </tr>
</table>
"""
    return html


def NewClientInquiryAccruedMail(
    url: str, organization_name: str, organization_logo: str, client_details: dict
):

    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "new-client-inquiry-mail.html")

    with open(path, "r") as file:
        html_content = file.read()

    # Format client details into HTML table rows
    client_details_html = format_client_details(client_details)

    html_content = (
        html_content.replace("{create_password_link}", url)
        .replace("{organization_name}", organization_name)
        .replace("{organization_logo}", organization_logo)
        .replace("{client_details}", client_details_html)
        .replace("{orbit_contact_emil}", ORBIT_CONTACT_EMAIL)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )

    return html_content


def NewAdminLoginGeneratedOtp(Otp_Code: str):

    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "admin-access-code.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = (
        (html_content.replace("{OTP_Code}", Otp_Code))
        .replace("{orbit_contact_emil}", ORBIT_CONTACT_EMAIL)
        .replace("{facebook_url}", FACEBOOK_LINK)
        .replace("{instagram_url}", INSTAGRAM_LINK)
        .replace("{linked_in_url}", LINKEDIN_LINK)
    )

    return html_content
