import bcrypt


def hash_password(plain_password: str) -> str:
    """Хеширует пароль с помощью bcrypt.

    Args:
        plain_password (str): пароль в открытом виде.

    Returns:
        str: хеш пароля, готовый для хранения в БД.
    """
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Проверяет, соответствует ли пароль сохранённому хешу.

    Args:
        plain_password (str): пароль в открытом виде, введённый пользователем.
        password_hash (str): хеш пароля, сохранённый в БД.

    Returns:
        bool: True, если пароль верный.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
