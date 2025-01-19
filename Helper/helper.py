import secrets


def generate_full_name(first_name:str , last_name:str = None) -> str:
 return f"{first_name} {last_name}"

def generate_random_secret_key()->str:
    generated_secret_key = secrets.token_urlsafe(16)
    print(generated_secret_key)
    return generated_secret_key