from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

EMAIL_TOKEN_MAX_AGE = 60 * 60 * 24  # 24 hours

signer = TimestampSigner()


def generate_email_token(user):
    return signer.sign(f"{user.pk}:{user.email}")


def verify_email_token(token):
    try:
        value = signer.unsign(token, max_age=EMAIL_TOKEN_MAX_AGE)
        pk, email = value.rsplit(":", 1)
        return int(pk), email
    except (BadSignature, SignatureExpired, ValueError):
        return None
