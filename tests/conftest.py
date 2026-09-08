"""Keep desktop tests from changing the developer's real preferences."""
import pytest
from PySide6.QtCore import QSettings


@pytest.fixture(autouse=True)
def isolated_desktop_preferences(tmp_path, monkeypatch):
    from neuroflow import tutorial_center, ui

    def settings(*_args):
        return QSettings(str(tmp_path / "desktop-test.ini"), QSettings.IniFormat)

    monkeypatch.setattr(ui, "QSettings", settings)
    monkeypatch.setattr(tutorial_center, "QSettings", settings)
