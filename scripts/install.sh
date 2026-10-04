#!/bin/sh
# NextPrompt installer for macOS / Linux:
# sh scripts/install.sh [--auto-copy on|off] [--notify on|off] [--probe]
set -eu

repo_root=$(cd "$(dirname "$0")/.." && pwd -P)
auto_copy=""
notify=""
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
        --notify)
            [ $# -ge 2 ] || fail "--notify needs on or off."
            notify=$2
            shift 2
            ;;
        --notify=*)
            notify=${1#--notify=}
            shift
            ;;
        --probe)
            probe="--probe"
            shift
            ;;
        *)
            fail "Unknown option: $1. Usage: sh scripts/install.sh [--auto-copy on|off] [--notify on|off] [--probe]"
            ;;
    esac
done
case "$auto_copy" in
    "" | on | off) ;;
    *) fail "--auto-copy must be on or off." ;;
esac
case "$notify" in
    "" | on | off) ;;
    *) fail "--notify must be on or off." ;;
esac

# Hooks run `python` or `python3`, so the installer accepts the same commands.
find_python() {
    python=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c "import sys; sys.exit(sys.version_info < (3, 9))" >/dev/null 2>&1; then
            python=$candidate
            return 0
        fi
    done
    return 1
}

as_root() {
    if [ "$(id -u)" = 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        fail "Installing Python needs administrator rights, and sudo is not available. Install Python 3.9+ yourself, then rerun this script."
    fi
}

# Install Python 3.9+ with the system's own package manager; nothing is downloaded by hand.
install_python() {
    echo "未找到 Python 3.9+，正在自动安装… / Python 3.9+ was not found. Installing it..."
    if [ "$(uname -s)" = Darwin ]; then
        if command -v brew >/dev/null 2>&1; then
            brew install python3 || fail "Homebrew could not install Python."
        else
            # Apple's Command Line Tools include /usr/bin/python3 (3.9+).
            xcode-select --install >/dev/null 2>&1 || true
            fail "macOS 正在弹窗安装命令行工具（含 Python），装好后请重新运行本脚本。 / macOS is installing the Command Line Tools (which include Python) in a separate window. Finish that, then rerun this script."
        fi
    elif command -v apt-get >/dev/null 2>&1; then
        as_root apt-get update && as_root apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then
        as_root dnf install -y python3
    elif command -v yum >/dev/null 2>&1; then
        as_root yum install -y python3
    elif command -v zypper >/dev/null 2>&1; then
        as_root zypper --non-interactive install python3
    elif command -v pacman >/dev/null 2>&1; then
        as_root pacman -S --noconfirm --needed python
    elif command -v apk >/dev/null 2>&1; then
        as_root apk add python3
    elif command -v brew >/dev/null 2>&1; then
        brew install python3
    else
        fail "No supported package manager was found. Install Python 3.9+ yourself, then rerun this script."
    fi || fail "Python could not be installed automatically. Install Python 3.9+ yourself, then rerun this script."
    hash -r 2>/dev/null || true
}

if ! find_python; then
    install_python
    find_python || fail "Python was installed, but no python3 or python command with 3.9+ is on PATH. Open a new terminal, then rerun this script."
fi
command -v codex >/dev/null 2>&1 || fail "Codex CLI is required. Install or repair Codex, then rerun this script."

echo "Python ready: $("$python" -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")"
codex plugin marketplace add "$repo_root" || fail "Could not register the local nextprompt marketplace."
codex plugin add "nextprompt@nextprompt" || fail "Could not install nextprompt@nextprompt."
# shellcheck disable=SC2086 # $probe is empty or one word.
"$python" "$repo_root/scripts/doctor.py" $probe || fail "NextPrompt Doctor reported a required check failure."

# Sets auto_copy and notify from a two-letter answer: 1st = copy, 2nd = notifications.
choose_pair() {
    case "$1" in
        yy) auto_copy=on notify=on ;;
        yn) auto_copy=on notify=off ;;
        ny) auto_copy=off notify=on ;;
        nn) auto_copy=off notify=off ;;
        *) return 1 ;;
    esac
}

ask() {
    printf "%s" "$1"
    read -r answer || fail "Preferences were not saved. Rerun, or pass --auto-copy on|off and --notify on|off."
    answer=$(printf "%s" "$answer" | tr -d ' \t' | tr 'A-Z' 'a-z')
}

# A flag skips the questions; a setting without a flag keeps the recommended value.
if [ -z "$auto_copy" ] && [ -z "$notify" ]; then
    [ -t 0 ] || fail "Preferences were not saved. Rerun interactively, or pass --auto-copy on|off and --notify on|off."
    echo ""
    echo "推荐设置 / Recommended settings:"
    echo "  自动复制到剪贴板：开（推荐） / Automatic clipboard copy: ON (recommended)"
    echo "  桌面通知：开（推荐） / Desktop notifications: ON (recommended)"
    echo "其他本地程序可能读取剪贴板。 / Other local applications may read clipboard contents."
    while [ -z "$auto_copy" ]; do
        ask "使用推荐设置？ / Keep the recommended settings? [Y/n]: "
        case "$answer" in
            "" | y | yes) auto_copy=on notify=on ;;
            n | no)
                echo "输入两个字母：第 1 个是自动复制，第 2 个是桌面通知（y = 开，n = 关）。"
                echo "Type two letters: 1st = automatic copy, 2nd = desktop notifications (y = on, n = off)."
                echo "  yn = 复制开、通知关 / copy on, notifications off"
                echo "  ny = 复制关、通知开 / copy off, notifications on"
                echo "  nn = 都关 / both off      yy = 都开 / both on"
                while [ -z "$auto_copy" ]; do
                    ask "yn / ny / nn / yy: "
                    choose_pair "$answer" || echo "请输入 yn、ny、nn 或 yy。 / Please enter yn, ny, nn or yy."
                done
                ;;
            # Accept a two-letter answer straight away, e.g. yn.
            *) choose_pair "$answer" || echo "请输入 Y 或 N。 / Please enter Y or N." ;;
        esac
    done
fi
[ -n "$auto_copy" ] || auto_copy=on
[ -n "$notify" ] || notify=on

"$python" "$repo_root/scripts/nextprompt.py" setup --auto-copy "$auto_copy" --notify "$notify" >/dev/null ||
    fail "Could not save the NextPrompt preferences."

echo ""
echo "NextPrompt 安装完成 / NextPrompt installed successfully."
if [ "$auto_copy" = on ]; then
    echo "自动复制：开，新建议会自动复制到剪贴板。 / Automatic clipboard copy: ON. New suggestions will be copied automatically."
else
    echo "自动复制：关，建议只显示不复制。 / Automatic clipboard copy: OFF. Suggestions will be displayed only."
fi
if [ "$notify" = on ]; then
    echo "桌面通知：开，建议准备好时弹出系统通知。 / Desktop notifications: ON. A notification appears when a suggestion is ready."
else
    echo "桌面通知：关。 / Desktop notifications: OFF."
fi
echo "以上选择已保存，其他已有设置保持不变，不需要再运行 setup。 / Your choices have been saved. Other existing settings are preserved. No additional setup is required."
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
echo "以后修改自动复制或通知：\$nextprompt-setup / Change clipboard copy or turn notifications on or off later: \$nextprompt-setup"
echo "暂停或恢复建议：\$nextprompt-disable、\$nextprompt-enable / Pause or resume suggestions: \$nextprompt-disable or \$nextprompt-enable"
echo "查看状态或排查：\$nextprompt-status、\$nextprompt-doctor / Help: \$nextprompt-status or \$nextprompt-doctor"
