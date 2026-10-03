from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import pytest

from nextprompt.config import DEFAULTS, ConfigStore


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    monkeypatch.delenv("NEXTPROMPT_INTERNAL", raising=False)


@pytest.fixture
def configured(tmp_path):
    store = ConfigStore(tmp_path / "data")
    store.update(lambda cfg: cfg["clipboard"].update(auto_copy=False))
    return store


@pytest.fixture
def settings():
    return deepcopy(DEFAULTS)


@pytest.fixture
def provider():
    return Mock(
        generate=Mock(return_value="Run the full regression suite and review the final diff."),
        selection=None,
    )


@pytest.fixture
def clipboard():
    return Mock(
        available=Mock(return_value=True),
        copy=Mock(return_value=True),
        backend_name=Mock(return_value="test-backend"),
    )
