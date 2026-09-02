from . import en, ru, uz

LOCALES = {"en": en.STRINGS, "ru": ru.STRINGS, "uz": uz.STRINGS}
DEFAULT_LANGUAGE = "uz"


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: object) -> str:
    template = LOCALES.get(lang, LOCALES[DEFAULT_LANGUAGE]).get(key, key)
    return template.format(**kwargs) if kwargs else template


def all_translations(key: str) -> set[str]:
    """Every language's rendering of a fixed string (e.g. a reply-keyboard button's label) — lets
    a handler match the button regardless of which language the user picked at /start."""
    return {strings.get(key, key) for strings in LOCALES.values()}
