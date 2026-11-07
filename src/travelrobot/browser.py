from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, Playwright, Response, async_playwright

logger = logging.getLogger(__name__)
T = TypeVar("T")

BLOCKED_STATUSES = {202, 403, 429}


class SourceBlocked(Exception):
    """O site recusou o acesso automatizado. Não é repetido nem contornado: só é reportado."""


def raise_if_blocked(response: Response | None, source: str) -> None:
    if response is not None and response.status in BLOCKED_STATUSES:
        raise SourceBlocked(f"{source} recusou o acesso automatizado (HTTP {response.status}).")


class Browser:
    """Um Chromium compartilhado, com um contexto isolado e descartável por página."""

    def __init__(self, headless: bool, concurrency: int, timeout_seconds: int) -> None:
        self._headless = headless
        self._semaphore = asyncio.Semaphore(concurrency)
        self._timeout_ms = timeout_seconds * 1000
        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None

    async def __aenter__(self) -> Browser:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @asynccontextmanager
    async def page(self) -> AsyncIterator[Page]:
        async with self._semaphore:
            context = await self._browser.new_context(
                locale="pt-BR", viewport={"width": 1280, "height": 800}
            )
            try:
                page = await context.new_page()
                page.set_default_timeout(self._timeout_ms)
                page.set_default_navigation_timeout(self._timeout_ms)
                yield page
            finally:
                await context.close()


async def with_retry(
    operation: Callable[[], Awaitable[T]], description: str, attempts: int = 2, delay: float = 3
) -> T:
    """Repete uma operação de navegador; ao esgotar as tentativas, propaga o último erro."""
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except PlaywrightError as error:
            if attempt == attempts:
                raise
            logger.warning("%s: tentativa %d falhou: %s", description, attempt, error)
            await asyncio.sleep(delay)
    raise AssertionError("attempts precisa ser >= 1")
