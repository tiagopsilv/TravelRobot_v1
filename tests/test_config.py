from pathlib import Path

import pytest

from travelrobot.cli import EXIT_CONFIG_ERROR, main
from travelrobot.config import ConfigError, load_config

SHIPPED_CONFIG = Path(__file__).parents[1] / "config" / "searches.toml"


def test_shipped_config_is_valid_and_keeps_accents():
    config = load_config(SHIPPED_CONFIG)
    enabled = [rule for rule in config.search if rule.enabled]
    assert [rule.city_name for rule in enabled] == ["LosAngeles"]
    assert enabled[0].text_for_search == "Santa Mônica, CA, EUA"


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="não encontrado"):
        load_config(tmp_path / "nada.toml")


def test_unknown_field_is_rejected(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text(
        '[[search]]\ncity_name="X"\ntext_for_search="X"\nreference_point="Y"\n'
        'start_date=2027-01-01\nend_date=2027-01-02\ncampo_errado=1\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="campo_errado"):
        load_config(path)


def test_cli_reports_config_error(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "nada.toml")]) == EXIT_CONFIG_ERROR
    assert "Erro de configuração" in capsys.readouterr().out
