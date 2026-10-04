"""Convert model text into one bounded, useful instruction."""

from __future__ import annotations

import math
import re
import unicodedata

from .redact import redact
from .transcript import Message

# Scripts written without spaces between words.
IDEOGRAPHIC = "぀-ヿ㐀-䶿一-鿿豈-﫿"  # kana and Han
UNSPACED = "฀-໿က-႟ក-៿"  # Thai, Lao, Myanmar, Khmer
COMPACT = re.compile(f"[{IDEOGRAPHIC}{UNSPACED}가-힯]")  # plus Hangul syllables


def _key(text: str) -> str:
    """Casefold and drop punctuation so 'Continue.' and '继续！' compare equal."""
    kept = "".join(c for c in text.casefold() if not unicodedata.category(c).startswith("P"))
    return " ".join(kept.split())


GENERIC = {
    _key(phrase)
    for phrase in (
        # English
        "continue",
        "keep working",
        "proceed",
        "check your work",
        "do more testing",
        "fix the issue",
        "continue working",
        "run tests",
        "run the tests",
        "do the next step",
        "yes",
        "no",
        "done",
        "okay",
        "ok",
        "next",
        "suggestion",
        "null",
        "none",
        # Chinese
        "继续",
        "继续工作",
        "继续执行",
        "继续处理",
        "继续下一步",
        "执行下一步",
        "做下一步",
        "检查工作",
        "检查一下",
        "修复问题",
        "修复这个问题",
        "运行测试",
        "跑一下测试",
        "好的",
        "没问题",
        "繼續",
        "繼續工作",
        "修復問題",
        "執行測試",
        # Japanese
        "続けて",
        "続けてください",
        "進めてください",
        "続行してください",
        "テストを実行して",
        "テストを実行してください",
        "はい",
        "いいえ",
        # Korean
        "계속",
        "계속해",
        "계속해 주세요",
        "계속 진행해 주세요",
        "진행해 주세요",
        "테스트 실행",
        "테스트를 실행해 주세요",
        "네",
        "아니요",
        # Spanish, Portuguese, French, German, Russian
        "continúa",
        "continuar",
        "sigue adelante",
        "ejecuta las pruebas",
        "continue trabalhando",
        "execute os testes",
        "rode os testes",
        "continuer",
        "continue le travail",
        "lance les tests",
        "weiter",
        "weitermachen",
        "mach weiter",
        "führe die tests aus",
        "продолжай",
        "продолжай работу",
        "запусти тесты",
    )
}

PREFIX = re.compile(
    r"^\s*(?:suggestion|next prompt|next step|next|prompt|"
    r"建议|建議|下一步|下一句|下一条|提示词|提示詞|"
    r"次のプロンプト|次のステップ|提案|다음 프롬프트|다음 단계|제안)\s*[:：→]\s*",
    re.I,
)
# Assistant voice or chatter rather than a user's instruction.
NOT_USER_VOICE = re.compile(
    r"[{}<>]|https?://|^#{1,6}\s|^I (?:have|will|can)\b|"
    r"^(?:here is|here's|as an ai|the next prompt is)\b|"
    r"^(?:我(?:会|将|已经|已|可以)|以下是|下面是|作为(?:一个)?\s*AI|"
    r"以下は|承知しました|다음은|알겠습니다)",
    re.I,
)


def word_count(text: str) -> int:
    """Count words across scripts; unspaced scripts count by characters."""
    ideographic = len(re.findall(f"[{IDEOGRAPHIC}]", text))
    unspaced = len(re.findall(f"[{UNSPACED}]", text))
    spaced = re.sub(f"[{IDEOGRAPHIC}{UNSPACED}]+", " ", text).split()
    words = sum(1 for token in spaced if any(c.isalnum() for c in token))
    # About two Han/kana characters, or four Thai-like letters, per English word.
    return words + math.ceil(ideographic / 2) + math.ceil(unspaced / 4)


def sanitize(raw: str, max_words: int = 20, max_chars: int = 240) -> str | None:
    if not isinstance(raw, str) or len(raw) > 16384:
        return None
    text = raw.strip()
    text = re.sub(r"^```[^\n]*\n?", "", text)
    text = text.replace("```", "").strip()
    text = PREFIX.sub("", text)
    text = text.strip(" \t\r\n\"'“”‘’`「」『』")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    text = re.sub(r"^(?:[-*]\s+|\d+[.)]\s+)", "", lines[0])
    text = re.split(r"(?<=[.!?。！？])\s+|(?<=[。！？])(?=\S)", text)[0].strip()
    # Inline code markers are formatting, not part of the instruction.
    text = text.replace("`", "").strip(" \t\"'“”‘’「」『』")
    # Reject control/format characters rather than hiding malicious terminal output.
    if any(unicodedata.category(c) in ("Cc", "Cf", "Cs") for c in text):
        return None
    if redact(text) != text:
        return None
    words = word_count(text)
    if not text or len(text) > min(240, max_chars) or words > min(20, max_words):
        return None
    # Compact scripts pack a full instruction into a few characters or spaces.
    if COMPACT.search(text):
        if len(text) < 4:
            return None
    elif len(text) < 8 or words < 3:
        return None
    if _key(text) in GENERIC:
        return None
    if NOT_USER_VOICE.search(text):
        return None
    if not any(c.isalpha() for c in text):
        return None
    return text


# Completed-work guards: (finished in the last assistant reply, suggestion repeats it).
# CJK patterns stay within one sentence, skip negations such as 还没通过 / 成功しませんでした,
# and accept both Simplified and Traditional Chinese.
_SAME = r"[^。！？.!?\n]*?"
_ZH_DONE = r"(?<!没有)(?<!沒有)(?<!没)(?<!沒)(?<!未)(?<!不)(?:通[过過]|全[绿綠]|完成|成功)"
_JA_DONE = r"(?:成功|通過|パス|完了)(?!しませ|していな|せず)"
_KO_DONE = r"(?:통과|완료|성공)(?!하지|되지)"
_ZH_TESTS = r"[测測][试試]"
_ZH_FULL = rf"(?:回[归歸](?:{_ZH_TESTS})?|(?:全量|完整|全部|所有){_ZH_TESTS})"
_ZH_RUN = r"^(?:[请請]|再)?(?:重新)?(?:[运運]行|跑|[执執]行|重跑)(?:一下|一遍|一次)?.*?"
_ZH_PR = r"(?:PR|拉取[请請]求|合[并併][请請]求)"
COMPLETED_WORK = (
    (
        r"(?:full regression|regression suite).*?(?:pass|green|complete)|"
        rf"{_ZH_FULL}{_SAME}{_ZH_DONE}|"
        rf"(?:回帰|全)テスト{_SAME}{_JA_DONE}|"
        rf"(?:회귀|전체)\s*테스트{_SAME}{_KO_DONE}",
        r"^(?:run|rerun|execute)\b.*?\b(?:regression|full test)|"
        rf"{_ZH_RUN}{_ZH_FULL}|"
        r"(?:回帰|全)テスト.*?(?:実行|走らせ)|"
        r"(?:회귀|전체)\s*테스트.*?(?:실행|돌려)",
    ),
    (
        r"targeted tests.*?(?:pass|green|complete)|"
        rf"(?:相[关關]|[针針][对對]性|定向){_ZH_TESTS}{_SAME}{_ZH_DONE}",
        r"^(?:run|rerun)\b.*?targeted tests|"
        rf"{_ZH_RUN}(?:相[关關]|[针針][对對]性|定向){_ZH_TESTS}",
    ),
    (
        r"(?:PR\s*#?\d+|pull request).*?(?:created|opened)|created.*?pull request|"
        rf"{_ZH_PR}{_SAME}(?:已(?:[创創]建|建立|[开開]|提交)|[创創]建好|[开開]好)|"
        rf"已(?:[创創]建|建立|[开開]|提交){_SAME}{_ZH_PR}|"
        rf"(?:PR|プルリクエスト){_SAME}(?:作成|オープン)しました|"
        rf"(?:PR|풀 리퀘스트){_SAME}(?:생성했|열었)",
        r"^(?:create|open)\b.*?pull request|"
        rf"^(?:[请請])?(?:[创創]建|建立|[开開]|提交|新建)(?:一个|一個)?.*?{_ZH_PR}|"
        r"(?:PR|プルリクエスト)\s*を\s*(?:作成|開)|"
        r"(?:PR|풀 리퀘스트).*?(?:생성|만들|열어)",
    ),
    (
        r"(?:CI|continuous integration).*?(?:pass|green|succeed)|"
        rf"CI{_SAME}{_ZH_DONE}|CI{_SAME}{_JA_DONE}|CI{_SAME}{_KO_DONE}",
        r"^(?:check|wait for)\b.*?\bCI\b.*?(?:results|complete|finish)|"
        r"^(?:[请請])?(?:[检檢]查|等待|查看|看看|等).*?CI.*?(?:[结結]果|完成|跑完)|"
        r"CI.*?(?:結果|完了).*?(?:確認|待)|"
        r"CI.*?(?:결과|완료).*?(?:확인|기다)",
    ),
)


def obvious_repeat(suggestion: str, context: list[Message]) -> bool:
    last = next((m.text for m in reversed(context) if m.role == "assistant"), "")
    return any(
        re.search(done, last, re.I | re.S) and re.search(action, suggestion, re.I)
        for done, action in COMPLETED_WORK
    )
