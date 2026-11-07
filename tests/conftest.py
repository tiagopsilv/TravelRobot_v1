from datetime import date
from pathlib import Path

import pytest

from travelrobot.config import load_selectors
from travelrobot.models import SearchWindow


@pytest.fixture(scope="session")
def selectors():
    return load_selectors(Path(__file__).parents[1] / "config" / "selectors.toml")


@pytest.fixture
def window():
    return SearchWindow(
        city_name="LosAngeles",
        city_code="CIT_1",
        text_for_search="Santa Mônica, CA, EUA",
        reference_point="Hollywood",
        website_url="https://www.decolar.com/",
        check_in=date(2027, 3, 23),
        check_out=date(2027, 3, 25),
    )
