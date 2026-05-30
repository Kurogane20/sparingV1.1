import secrets

def generate_device_secret() -> str:
    """Generate a 64-character hex secret for a site's IoT devices."""
    return secrets.token_hex(32)

def mask_secret(secret: str) -> str:
    """Return first 4 chars + bullets, e.g. 'a1b2••••••••'."""
    if not secret:
        return "••••••••"
    visible = secret[:4]
    return visible + "••••"
