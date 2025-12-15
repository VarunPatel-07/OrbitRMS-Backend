from fastapi import BackgroundTasks

from Config.EnvConfig import EnvConfig
from Email.HtmlEmailBody import WelcomeMailNewOrganization
from Helper.emailSender import EmailSchema, email_sender_function
from PydanticModels.HelperPydanticModel import NewOrganizationCreatedSuccessFully
from PydanticModels.Organizations.organizations import OnboardingOrganization

FRONTEND_URL = EnvConfig.FRONTEND_URL


def OnboardingCompletedMailSending(data: OnboardingOrganization, background_task: BackgroundTasks):
    emil_body_data = {
        "user_name": data.employee_profile_info.full_name,
        "organization_name": data.general_info.organization_name,
        "organization_dashboard_link": f"{FRONTEND_URL}/{data.general_info.portal_slug}/dashboard",
    }

    email_data = {
        "recever_email": data.general_info.primary_email,
        "subject": f"Welcome {data.employee_profile_info.full_name} to {data.general_info.organization_name} – We're excited to have you onboard!",
        "body": WelcomeMailNewOrganization(NewOrganizationCreatedSuccessFully(**emil_body_data)),
    }

    email_instance = EmailSchema(**email_data)

    email_sender_function(email_instance, background_task)
