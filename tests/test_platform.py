import pytest

from nextprompt.platform import detect_platform


@pytest.mark.parametrize(
    ("system", "release", "env", "expected"),
    [
        ("Windows", "10", {}, "windows"),
        ("Darwin", "24", {}, "macos"),
        ("Linux", "6-microsoft-standard-WSL2", {}, "wsl"),
        ("Linux", "6", {"WSL_INTEROP": "present"}, "wsl"),
        ("Linux", "6", {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}, "wayland"),
        ("Linux", "6", {"DISPLAY": ":0"}, "x11"),
        ("Linux", "6", {}, "headless"),
        ("Other", "1", {}, "headless"),
    ],
)
def test_detection(system, release, env, expected):
    assert detect_platform(system, release, env).name == expected
