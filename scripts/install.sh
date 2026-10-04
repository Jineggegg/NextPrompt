#!/bin/sh
# NextPrompt installer for macOS / Linux: sh scripts/install.sh [--auto-copy on|off] [--probe]
set -eu

repo_root=$(cd "$(dirname "$0")/.." && pwd -P)
auto_copy=""
probe=""

fail() {
    echo "$1" >&2
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --auto-copy)
            [ $# -ge 2 ] || fail "--auto-copy needs on or off."
            auto_copy=$2
            shift 2
            ;;
        --auto-copy=*)
            auto_copy=${1#--auto-copy=}
            shift
            ;;
        --probe)
            probe="--probe"
            shift
            ;;
        *)
            fail "Unknown option: $1. Usage: sh scripts/install.sh [--auto-copy on|off] [--probe]"
            ;;
    esac
done
case "$auto_copy" in
    "" | on | off) ;;
    *) fail "--auto-copy must be on or off." ;;
esac

# Hooks run `python` or `python3`, so the installer accepts the same commands.
python=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
        "$candidate" -c "import sys; sys.exit(sys.version_info < (3, 9))" >/dev/null 2>&1; then
        python=$candidate
        break
    fi
done
[ -n "$python" ] || fail "Python 3.9+ is required as python3 or python. Install it, then rerun this script."
command -v codex >/dev/null 2>&1 || fail "Codex CLI is required. Install or repair Codex, then rerun this script."

echo "Python ready: $("$python" -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")"
codex plugin marketplace add "$repo_root" || fail "Could not register the local nextprompt marketplace."
codex plugin add "nextprompt@nextprompt" || fail "Could not install nextprompt@nextprompt."
# shellcheck disable=SC2086 # $probe is empty or one word.
"$python" "$repo_root/scripts/doctor.py" $probe || fail "NextPrompt Doctor reported a required check failure."

if [ -z "$auto_copy" ]; then
    [ -t 0 ] || fail "Clipboard preference was not saved. Rerun interactively, or pass --auto-copy on|off."
    echo ""
    echo "是否自动把下一步建议复制到剪贴板？ / Automatically copy suggested next prompts to your clipboard?"
    echo "Y = 自动复制（默认） / automatic copy (default); N = 仅展示 / display only."
    echo "其他本地程序可能读取剪贴板。 / Other local applications may read clipboard contents."
    while [ -z "$auto_copy" ]; do
        printf "Choose Y or N [Y]: "
        read -r answer || fail "Clipboard preference was not saved. Rerun, or pass --auto-copy on|off."
        case "$answer" in
            "" | y | Y | yes | YES | Yes) auto_copy=on ;;
            n | N | no | NO | No) auto_copy=off ;;
            *) echo "Please enter Y or N." ;;
        esac
    done
fi

"$python" "$repo_root/scripts/nextprompt.py" setup --auto-copy "$auto_copy" >/dev/null ||
    fail "Could not save the NextPrompt clipboard preference."

echo ""
echo "NextPrompt 安装完成 / NextPrompt installed successfully."
if [ "$auto_copy" = on ]; then
    echo "自动复制：开，新建议会自动复制到剪贴板。 / Automatic clipboard copy: ON. New suggestions will be copied automatically."
else
    echo "自动复制：关，建议只显示不复制。 / Automatic clipboard copy: OFF. Suggestions will be displayed only."
fi
echo "桌面通知：默认开，可以单独关闭。 / Desktop notifications: ON by default; you can turn them off without disabling suggestions."
echo "其他已有设置保持不变，不需要再运行 setup。 / Other existing settings are preserved. No additional setup is required."
echo ""
echo "接下来在 Codex 里 / Finish in Codex:"
echo "1. 完全退出并重新打开 Codex。 / Fully quit and reopen Codex to load the plugin."
echo "2. 打开 /hooks，检查并信任 NextPrompt 的 SessionStart、UserPromptSubmit 和 Stop Hook。"
echo "   / Open /hooks, review the NextPrompt SessionStart, UserPromptSubmit and Stop hooks, and trust them."
echo "   安装不会替你信任 Hook。 / Installation does not grant hook trust or bypass your approval."
echo "3. 正常聊一轮。每条回复末尾会有一行下一步建议，例如："
echo "   / Complete a normal conversation turn. Each reply ends with a suggestion such as:"
echo "   Next prompt: Run the full regression suite and review the final diff."
echo "   建议不会自动发送，请检查后自己粘贴发送。 / It is never sent automatically; review, paste and send it yourself."
echo ""
echo "修改设置或关闭通知：\$nextprompt-setup / Change settings or turn off notifications: \$nextprompt-setup"
echo "查看状态或排查：\$nextprompt-status、\$nextprompt-doctor / Help: \$nextprompt-status or \$nextprompt-doctor"
