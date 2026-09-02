from . import en, ru, uz

LOCALES = {"en": en.STRINGS, "ru": ru.STRINGS, "uz": uz.STRINGS}
DEFAULT_LANGUAGE = "uz"


def t(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    return LOCALES.get(lang, LOCALES[DEFAULT_LANGUAGE]).get(key, key)
