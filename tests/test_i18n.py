import pytest

from nextprompt.i18n import LANGUAGES, MESSAGES, detect_language, message, resolve_language
from nextprompt.output import SuggestionResult, render


def test_every_language_has_every_message():
    keys = set(MESSAGES["en"])
    for language in LANGUAGES:
        assert set(MESSAGES[language]) == keys
        assert all(text.strip() for text in MESSAGES[language].values())


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Fix the login redirect.", "en"),
        ("帮我修复登录跳转的问题", "zh"),
        ("幫我修復登入跳轉的問題", "zh-TW"),
        ("ログインのリダイレクトを直して", "ja"),
        ("로그인 리다이렉트를 고쳐 줘", "ko"),
        ("Исправь редирект после входа", "ru"),
        ("修一下这个 bug", "zh"),
        ("Corrige la redirección del login", "en"),
    ],
)
def test_detect_language_by_script(text, language):
    assert detect_language(text) == language


def test_resolve_language():
    assert resolve_language("de", ["帮我修复"]) == "de"
    assert resolve_language("auto", ["", "帮我修复"]) == "zh"
    assert resolve_language("auto", []) == "en"


@pytest.mark.parametrize("language", LANGUAGES)
def test_render_uses_only_localized_labels(language):
    result = SuggestionResult("Run the suite.", "codex", "m", 2, True, "pbcopy")
    assert render(result, False, language) == f"{message(language, 'display')}\nRun the suite."
    assert render(result, True, language).endswith(message(language, "copied"))


def test_unknown_language_falls_back_to_english():
    assert message("xx", "display") == "Next prompt:"
