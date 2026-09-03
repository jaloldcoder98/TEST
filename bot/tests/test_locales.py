"""Every user-facing string must go through locales.t()/all_translations() (spec.md §21: no
hardcoded UI strings) — which only works if en/ru/uz actually define the same set of keys. A key
present in one language and silently missing in another doesn't error at runtime (t() falls back
to the raw key), so it has to be caught here instead of by a user noticing English text in the
Uzbek flow.
"""

from __future__ import annotations

from locales import DEFAULT_LANGUAGE, LOCALES, all_translations, t


def test_default_language_is_a_known_locale():
    assert DEFAULT_LANGUAGE in LOCALES


def test_every_locale_defines_the_same_keys():
    key_sets = {lang: set(strings.keys()) for lang, strings in LOCALES.items()}
    reference_lang, reference_keys = next(iter(key_sets.items()))
    for lang, keys in key_sets.items():
        missing = reference_keys - keys
        extra = keys - reference_keys
        assert not missing, f"{lang} is missing keys present in {reference_lang}: {sorted(missing)}"
        assert not extra, f"{lang} has keys not present in {reference_lang}: {sorted(extra)}"


def test_t_falls_back_to_default_language_for_an_unknown_language_code():
    assert t("common.cancelled", "xx") == t("common.cancelled", DEFAULT_LANGUAGE)


def test_t_formats_placeholders():
    rendered = t("welcome_back", "en", name="Bek")
    assert rendered == "Welcome back, Bek!"


def test_t_returns_the_raw_key_for_an_unknown_key_rather_than_crashing():
    assert t("nonexistent.key", "en") == "nonexistent.key"


def test_all_translations_covers_every_locale_for_a_shared_key():
    variants = all_translations("menu.ai_coach")
    assert variants == {LOCALES["en"]["menu.ai_coach"], LOCALES["ru"]["menu.ai_coach"], LOCALES["uz"]["menu.ai_coach"]}
    assert len(variants) == 3  # the three languages actually differ, not all falling back to the same string
