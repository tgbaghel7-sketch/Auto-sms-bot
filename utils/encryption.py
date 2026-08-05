# Encryption removed for simplicity.
# Credentials are stored as plain text in the database.
# Do not share your database or logs with others.

def encrypt(text: str) -> str:
    if not text:
        return ""
    return text


def decrypt(token: str) -> str:
    if not token:
        return ""
    return token
