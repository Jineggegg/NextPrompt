"""Localized display text. The language follows the conversation unless configured."""

from __future__ import annotations

import re
from collections.abc import Iterable

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "notify_copied": "Next prompt copied",
        "notify": "Next prompt",
        "display": "Next prompt:",
        "next": "Next →",
        "copied": "✓ Copied to clipboard",
        "osc52": "Clipboard copy requested (OSC 52; unverified).",
        "unavailable": "Clipboard unavailable — copy the prompt above manually.",
        "skipped": "NextPrompt skipped: suggestion model unavailable.",
    },
    "zh": {
        "notify_copied": "下一句已复制",
        "notify": "下一句",
        "display": "下一句：",
        "next": "下一句 →",
        "copied": "✓ 已复制到剪贴板",
        "osc52": "已请求复制到剪贴板（OSC 52，无法确认）。",
        "unavailable": "剪贴板不可用，请手动复制上面的提示词。",
        "skipped": "NextPrompt 已跳过：建议模型暂不可用。",
    },
    "zh-TW": {
        "notify_copied": "下一句已複製",
        "notify": "下一句",
        "display": "下一句：",
        "next": "下一句 →",
        "copied": "✓ 已複製到剪貼簿",
        "osc52": "已要求複製到剪貼簿（OSC 52，無法確認）。",
        "unavailable": "剪貼簿無法使用，請手動複製上面的提示詞。",
        "skipped": "NextPrompt 已略過：建議模型暫時無法使用。",
    },
    "ja": {
        "notify_copied": "次のプロンプトをコピーしました",
        "notify": "次のプロンプト",
        "display": "次のプロンプト：",
        "next": "次へ →",
        "copied": "✓ クリップボードにコピーしました",
        "osc52": "クリップボードへのコピーを要求しました（OSC 52、未確認）。",
        "unavailable": "クリップボードを利用できません。上のプロンプトを手動でコピーしてください。",
        "skipped": "NextPrompt をスキップしました：提案モデルを利用できません。",
    },
    "ko": {
        "notify_copied": "다음 프롬프트를 복사했습니다",
        "notify": "다음 프롬프트",
        "display": "다음 프롬프트:",
        "next": "다음 →",
        "copied": "✓ 클립보드에 복사했습니다",
        "osc52": "클립보드 복사를 요청했습니다(OSC 52, 확인 불가).",
        "unavailable": "클립보드를 사용할 수 없습니다. 위 프롬프트를 직접 복사하세요.",
        "skipped": "NextPrompt 건너뜀: 제안 모델을 사용할 수 없습니다.",
    },
    "es": {
        "notify_copied": "Siguiente prompt copiado",
        "notify": "Siguiente prompt",
        "display": "Siguiente prompt:",
        "next": "Siguiente →",
        "copied": "✓ Copiado al portapapeles",
        "osc52": "Copia al portapapeles solicitada (OSC 52; sin verificar).",
        "unavailable": "Portapapeles no disponible: copia manualmente el prompt de arriba.",
        "skipped": "NextPrompt omitido: modelo de sugerencias no disponible.",
    },
    "fr": {
        "notify_copied": "Prochain prompt copié",
        "notify": "Prochain prompt",
        "display": "Prochain prompt :",
        "next": "Suivant →",
        "copied": "✓ Copié dans le presse-papiers",
        "osc52": "Copie dans le presse-papiers demandée (OSC 52 ; non vérifiée).",
        "unavailable": "Presse-papiers indisponible : copiez le prompt ci-dessus manuellement.",
        "skipped": "NextPrompt ignoré : modèle de suggestion indisponible.",
    },
    "de": {
        "notify_copied": "Nächster Prompt kopiert",
        "notify": "Nächster Prompt",
        "display": "Nächster Prompt:",
        "next": "Weiter →",
        "copied": "✓ In die Zwischenablage kopiert",
        "osc52": "Kopieren in die Zwischenablage angefordert (OSC 52; unbestätigt).",
        "unavailable": "Zwischenablage nicht verfügbar – kopiere den Prompt oben manuell.",
        "skipped": "NextPrompt übersprungen: Vorschlagsmodell nicht verfügbar.",
    },
    "pt": {
        "notify_copied": "Próximo prompt copiado",
        "notify": "Próximo prompt",
        "display": "Próximo prompt:",
        "next": "Próximo →",
        "copied": "✓ Copiado para a área de transferência",
        "osc52": "Cópia para a área de transferência solicitada (OSC 52; não verificada).",
        "unavailable": "Área de transferência indisponível — copie o prompt acima manualmente.",
        "skipped": "NextPrompt ignorado: modelo de sugestões indisponível.",
    },
    "ru": {
        "notify_copied": "Следующий запрос скопирован",
        "notify": "Следующий запрос",
        "display": "Следующий запрос:",
        "next": "Далее →",
        "copied": "✓ Скопировано в буфер обмена",
        "osc52": "Запрошено копирование в буфер обмена (OSC 52; без подтверждения).",
        "unavailable": "Буфер обмена недоступен — скопируйте запрос выше вручную.",
        "skipped": "NextPrompt пропущен: модель подсказок недоступна.",
    },
}
LANGUAGES = tuple(MESSAGES)

# Characters that differ between Traditional and Simplified Chinese.
_TRADITIONAL = set(
    "們這個來時會說對過還麼後與實現開關試測請將為點運體經應發問題"
    "處機檔碼錯誤執讓給從進變據庫頁檢統專條復動寫讀設計認證錄層傳數"
)
_SIMPLIFIED = set(
    "们这个来时会说对过还么后与实现开关试测请将为点运体经应发问题"
    "处机档码错误执让给从进变据库页检统专条复动写读设计认证录层传数"
)


def detect_language(text: str) -> str:
    """Display languages that a script identifies reliably; Latin scripts use English."""
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[가-힯]", text):
        return "ko"
    if re.search(r"[㐀-鿿]", text):
        traditional = sum(c in _TRADITIONAL for c in text)
        return "zh-TW" if traditional > sum(c in _SIMPLIFIED for c in text) else "zh"
    if re.search(r"[Ѐ-ӿ]", text):
        return "ru"
    return "en"


def resolve_language(setting: str, texts: Iterable[str]) -> str:
    """Use the configured language, else the first non-empty text (latest user message)."""
    if setting in MESSAGES:
        return setting
    return next((detect_language(t) for t in texts if t and t.strip()), "en")


def message(language: str, key: str) -> str:
    return MESSAGES.get(language, MESSAGES["en"])[key]
