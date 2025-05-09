import os


def VerifyEmailHtmlBody(url: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "EmailVerification.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = html_content.replace("{verification_link}", url)
    return html_content


def CreatePasswordHtmlBody(url: str):
    base_url = os.path.dirname(__file__)
    path = os.path.join(base_url, "Html", "CreatePassword.html")
    with open(path, "r") as file:
        html_content = file.read()
    html_content = html_content.replace("{create_password_link}", url)
    return html_content
