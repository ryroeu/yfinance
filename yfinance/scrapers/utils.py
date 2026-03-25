"""Internal scraper helpers shared by quote-summary consumers."""

from collections.abc import Callable
from typing import Any, Optional

import curl_cffi

from yfinance.config import YF_CONFIG as YfConfig
from yfinance.data import YfData
from .. import utils


def get_raw_json_or_none(
    fetcher: Callable[[], dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Fetch raw JSON and suppress recoverable Yahoo HTTP errors when configured."""
    try:
        return fetcher()
    except curl_cffi.requests.exceptions.HTTPError as err:
        if YfConfig.debug.raise_on_error:
            raise
        response_text = err.response.text if err.response is not None else ""
        utils.get_yf_logger().error("%s%s", err, response_text)
        return None


def fetch_quote_summary(
    data: YfData,
    symbol: str,
    modules: list[str],
) -> Optional[dict[str, Any]]:
    """Fetch selected quote-summary modules for one symbol."""
    return get_raw_json_or_none(
        lambda: data.subscription.fetch_quote_summary(symbol, modules)
    )
