from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import quote, urljoin

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import GoogleHotelsSelectors
from travelrobot.models import GuestReviews, HotelOffer, SearchWindow
from travelrobot.parsing import extract_external_link, parse_currency, parse_decimal, parse_int
from travelrobot.sources._html import attr_of, soup, text_of

logger = logging.getLogger(__name__)

BASE_URL = "https://www.google.com.br"
MAX_SCROLLS = 30
RESULTS_REFRESH_MS = 3000
DATE_CHECK_ATTEMPTS = 10
REVIEWS_TIMEOUT_MS = 10_000
MONTHS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
_REVIEW_SUMMARY = re.compile(r"(?P<rating>\d[\d,.]*) de 5 estrelas em (?P<count>\d[\d.]*) avalia")
_TOPIC = re.compile(r".+ \(\d[\d.]*\)")


class DatesNotApplied(Exception):
    """As datas pedidas não entraram na busca; os preços seriam de outra estadia."""


@dataclass(frozen=True, slots=True)
class HotelCandidate:
    name: str
    url: str
    rating: Decimal | None


def parse_hotel_list(html: str, selectors: GoogleHotelsSelectors) -> list[HotelCandidate]:
    candidates = []
    for card in soup(html).select(selectors.hotel_card):
        name = text_of(card, selectors.hotel_name)
        href = attr_of(card, selectors.hotel_link, "href")
        if name and href:
            candidates.append(
                HotelCandidate(
                    name=name,
                    url=urljoin(BASE_URL, href),
                    rating=parse_decimal(text_of(card, selectors.hotel_rating)),
                )
            )
    return candidates


def parse_offers(
    html: str,
    hotel: HotelCandidate,
    window: SearchWindow,
    selectors: GoogleHotelsSelectors,
    now: datetime,
) -> list[HotelOffer]:
    document = soup(html)
    address = text_of(document, selectors.address)
    offers = []
    for card in document.select(selectors.offer):
        price_text = text_of(card, selectors.offer_price)
        price = parse_decimal(price_text)
        site = text_of(card, selectors.offer_site)
        if price is None or not site:
            continue
        offers.append(
            HotelOffer(
                executed_at=now,
                source=site,
                city_name=window.city_name,
                hotel_name=hotel.name,
                check_in=window.check_in,
                check_out=window.check_out,
                price=price,
                currency=parse_currency(price_text),
                rating=hotel.rating,
                address=address,
                link=extract_external_link(attr_of(card, selectors.offer_link, "href")),
                html=str(card),
            )
        )
    return offers


def parse_reviews(html: str, selectors: GoogleHotelsSelectors) -> GuestReviews | None:
    """Lê só o bloco do hotel aberto: a página também traz as notas de todos os hotéis da lista."""
    block = soup(html).select_one(selectors.reviews_block)
    if block is None:
        return None

    reviews = GuestReviews()
    summary = attr_of(block, selectors.reviews_summary, "aria-label") or ""
    match = _REVIEW_SUMMARY.search(summary)
    if match:
        reviews.rating = parse_decimal(match["rating"])
        reviews.review_count = parse_int(match["count"])

    for button in block.select(selectors.topic_button):
        topic = text_of(button, selectors.topic_label) or ""
        if not _TOPIC.fullmatch(topic):  # "Pesquisar avaliações", "Tudo", "Mais 10"
            continue
        classes = button.get("class", [])
        if selectors.topic_positive_class in classes:
            reviews.positive_topics.append(topic)
        elif selectors.topic_negative_class in classes:
            reviews.negative_topics.append(topic)

    for site in block.select(selectors.other_site):
        name = text_of(site, selectors.other_site_name)
        score = text_of(site, selectors.other_site_score)
        if name and score:
            reviews.other_sites.append(f"{name}: {score}")
    return reviews


class GoogleHotelsSource:
    name = "Google Hotels"

    def __init__(self, browser: Browser, selectors: GoogleHotelsSelectors) -> None:
        self._browser = browser
        self._selectors = selectors

    async def collect(self, window: SearchWindow) -> list[HotelOffer]:
        html = await with_retry(lambda: self._fetch_list(window), f"Google Hotels {window.city_name}")
        hotels = parse_hotel_list(html, self._selectors)
        logger.info("Google Hotels: %d hotéis em %s", len(hotels), window.city_name)
        results = await asyncio.gather(*(self._collect_hotel(window, hotel) for hotel in hotels))
        return [offer for offers in results for offer in offers]

    async def _collect_hotel(self, window: SearchWindow, hotel: HotelCandidate) -> list[HotelOffer]:
        """A falha de um hotel é registrada e não interrompe os demais."""
        try:
            prices_html, reviews_html = await with_retry(
                lambda: self._fetch_hotel(hotel.url), f"Preços de {hotel.name}"
            )
        except PlaywrightError:
            logger.exception("Google Hotels: falha ao obter preços de %s", hotel.name)
            return []
        offers = parse_offers(prices_html, hotel, window, self._selectors, datetime.now())
        reviews = parse_reviews(reviews_html, self._selectors) if reviews_html else None
        for offer in offers:
            offer.reviews = reviews
        return offers

    async def _fetch_list(self, window: SearchWindow) -> str:
        selectors = self._selectors
        async with self._browser.page() as page:
            response = await page.goto(f"{BASE_URL}/travel/hotels/{quote(window.text_for_search)}")
            raise_if_blocked(response, "Google Hotels")
            await _set_date(page, selectors.check_in_input, window.check_in)
            await _set_date(page, selectors.check_out_input, window.check_out)
            await _require_date(page, selectors.check_in_input, window.check_in)
            await page.wait_for_selector(selectors.hotel_card, state="attached")
            await _scroll_to_bottom(page)
            return await page.content()

    async def _fetch_hotel(self, url: str) -> tuple[str, str | None]:
        """Devolve o HTML dos preços e o das avaliações, lidos na mesma visita à página."""
        selectors = self._selectors
        async with self._browser.page() as page:
            await page.goto(url)
            prices_tab = page.locator(selectors.prices_tab).first
            if await prices_tab.count() == 0:
                return await page.content(), None
            await prices_tab.click()
            await page.wait_for_selector(selectors.offer, state="attached")
            prices_html = await page.content()
            return prices_html, await self._read_reviews(page)

    async def _read_reviews(self, page: Page) -> str | None:
        """Casas de temporada costumam não ter avaliações; os preços já lidos não se perdem."""
        selectors = self._selectors
        try:
            await page.locator(selectors.reviews_tab).first.click()
            await page.wait_for_selector(
                selectors.reviews_block, state="attached", timeout=REVIEWS_TIMEOUT_MS
            )
        except PlaywrightError as error:
            logger.info("Google Hotels: sem avaliações: %s", str(error).splitlines()[0])
            return None
        return await page.content()


def date_matches(displayed: str, expected: date) -> bool:
    """Compara com o texto do campo, como "qui., 25 de mar."; o campo não mostra o ano."""
    label = rf"\b{expected.day} de {MONTHS[expected.month - 1]}"
    return re.search(label, displayed, re.IGNORECASE) is not None


async def _set_date(page: Page, selector: str, day: date) -> None:
    """Enter confirma o campo e atualiza a página; preencher o próximo antes disso perde o valor."""
    await page.fill(selector, f"{day:%d/%m/%Y}")
    await page.press(selector, "Enter")
    await page.wait_for_timeout(RESULTS_REFRESH_MS)
    await _require_date(page, selector, day)


async def _require_date(page: Page, selector: str, day: date) -> None:
    displayed = ""
    for _ in range(DATE_CHECK_ATTEMPTS):
        displayed = await page.locator(selector).first.input_value()
        if date_matches(displayed, day):
            return
        await page.wait_for_timeout(500)
    raise DatesNotApplied(f"Google Hotels: esperava {day:%d/%m/%Y}, mas o campo mostra {displayed!r}.")


async def _scroll_to_bottom(page: Page) -> None:
    height = 0
    for _ in range(MAX_SCROLLS):
        new_height = await page.evaluate(
            "() => { window.scrollTo(0, document.body.scrollHeight);"
            " return document.body.scrollHeight; }"
        )
        if new_height == height:
            return
        height = new_height
        await page.wait_for_timeout(1500)
    logger.warning("Google Hotels: limite de %d rolagens atingido.", MAX_SCROLLS)
