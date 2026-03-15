def get_user_error_message(exc: Exception, default_message: str) -> str:
    return getattr(exc, "user_message", default_message)