from __future__ import annotations

import argparse
import asyncio
import logging
import logging.handlers
from datetime import date
from pathlib import Path

from travelrobot.browser import Browser
from travelrobot.config import AppConfig, ConfigError, Selectors, load_config, load_selectors
from travelrobot.dates import build_windows
from travelrobot.models import RunReport, SearchWindow
from travelrobot.pipeline import Sources, run_pipeline
from travelrobot.sources.decolar import DecolarSource
from travelrobot.sources.esfera import EsferaSource
from travelrobot.sources.feeds import FeedSource
from travelrobot.sources.google_hotels import GoogleHotelsSource
from travelrobot.sources.google_maps import GoogleMapsSource
from travelrobot.sources.livelo import livelo_sources
from travelrobot.sources.pontos_pra_voar import PontosPraVoarSource
from travelrobot.sources.smiles import SmilesSource

logger = logging.getLogger("travelrobot")

EXIT_OK = 0
EXIT_NO_OFFERS = 1
EXIT_CONFIG_ERROR = 2


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="travelrobot", description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/searches.toml"))
    parser.add_argument("--selectors", type=Path, default=None, help="padrão: selectors.toml ao lado de --config")
    parser.add_argument("--headed", action="store_true", help="mostra o navegador")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def _setup_logging(log_dir: Path, verbose: bool) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_dir / "travelrobot.log", when="midnight", backupCount=14, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), file_handler],
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def _run(
    config: AppConfig, selectors: Selectors, windows: list[SearchWindow], headed: bool, today: date
) -> RunReport:
    settings = config.settings
    headless = settings.headless and not headed
    async with Browser(headless, settings.concurrency, settings.timeout_seconds) as browser:
        sources = Sources(
            offers=[
                GoogleHotelsSource(browser, selectors.google_hotels),
                DecolarSource(browser, selectors.decolar, settings.decolar_max_pages),
            ],
            promotions=[
                SmilesSource(browser, selectors.smiles),
                PontosPraVoarSource(browser, selectors.pontos_pra_voar),
                *livelo_sources(browser, selectors.livelo),
                EsferaSource(browser, selectors.esfera),
                *(FeedSource(browser, feed) for feed in selectors.feeds),
            ],
            distances=GoogleMapsSource(browser, selectors.google_maps),
        )
        return await run_pipeline(windows, sources, settings.output_dir, today)


def _log_summary(report: RunReport) -> None:
    logger.info(
        "Resumo: %d promoções, %d ofertas de %d hotéis, %d com avaliação, %d com distância.",
        report.promotions, report.offers, report.hotels,
        report.hotels_with_reviews, report.hotels_with_distance,
    )  # fmt: skip
    for source, count in sorted(report.promotions_by_source.items()):
        logger.info("  %s: %d promoções", source, count)
    for source, count in sorted(report.offers_by_source.items()):
        logger.info("  %s: %d ofertas", source, count)
    if report.failures:
        logger.warning("%d falhas durante a execução:", len(report.failures))
        for failure in report.failures:
            logger.warning("  %s", failure.splitlines()[0])


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    today = date.today()
    try:
        config = load_config(args.config)
        selectors = load_selectors(args.selectors or args.config.with_name("selectors.toml"))
        windows = build_windows(config.search, today)
    except ConfigError as error:
        print(f"Erro de configuração: {error}")
        return EXIT_CONFIG_ERROR
    if not windows:
        print("Erro de configuração: nenhuma busca habilitada.")
        return EXIT_CONFIG_ERROR

    _setup_logging(config.settings.log_dir, args.verbose)
    report = asyncio.run(_run(config, selectors, windows, args.headed, today))
    _log_summary(report)
    return EXIT_OK if report.offers else EXIT_NO_OFFERS
