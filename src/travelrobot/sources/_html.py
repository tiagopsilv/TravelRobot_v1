from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def text_of(root: Tag, selector: str) -> str | None:
    element = root.select_one(selector)
    if element is None:
        return None
    return " ".join(element.get_text(" ", strip=True).split()) or None


def attr_of(root: Tag, selector: str, attribute: str) -> str | None:
    element = root.select_one(selector)
    value = element.get(attribute) if element is not None else None
    return value if isinstance(value, str) and value else None
