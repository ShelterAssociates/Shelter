SHELTER_EMAIL_DOMAIN = "@shelter-associates.org"


def validate_shelter_email(email):
    """
    True only for a non-blank email ending in @shelter-associates.org (case-insensitive).
    Used to gate background/email-delivered exports to org members only.
    """
    if not email:
        return False
    return email.strip().lower().endswith(SHELTER_EMAIL_DOMAIN)
