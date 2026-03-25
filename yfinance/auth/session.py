"""Session utilities for Yahoo authentication flows."""

from typing import Any, Dict

from curl_cffi import requests

from ..config import YF_CONFIG as YfConfig
from ..exceptions import YFDataException


def create_default_session() -> requests.session.Session:
    """Return the default curl_cffi session used for Yahoo requests."""
    return requests.Session(impersonate="chrome")


def validate_session(session: requests.session.Session) -> bool:
    """Validate the caller-provided session and return caching state."""
    try:
        session.cache
    except AttributeError:
        session_is_caching = False
    else:
        session_is_caching = True
        raise YFDataException(
            "request_cache sessions don't work with curl_cffi, which is necessary "
            "now for Yahoo API. Solution: stop setting session, let YF handle."
        )

    if not isinstance(session, requests.session.Session):
        raise YFDataException(
            f"Yahoo API requires curl_cffi session not {type(session)}. "
            "Solution: stop setting session, let YF handle."
        )

    return session_is_caching


def resolve_proxy_config() -> Any:
    """Resolve proxy configuration from the global config object."""
    proxy_config = YfConfig.network.proxy
    if callable(proxy_config):
        proxy_config = proxy_config()
    if isinstance(proxy_config, str):
        return {"http": proxy_config, "https": proxy_config}
    return proxy_config


def sync_session_proxy(session: requests.session.Session) -> None:
    """Synchronize proxy settings onto the active session."""
    session.proxies = resolve_proxy_config()


def get_network_request_options(session: requests.session.Session) -> Dict[str, Any]:
    """Return request options derived from current network config."""
    sync_session_proxy(session)
    request_options: Dict[str, Any] = {}
    if YfConfig.network.verify is not None:
        request_options["verify"] = YfConfig.network.verify
    return request_options


def session_cookie_store(session: requests.session.Session) -> Dict[str, Any]:
    """Return the underlying mutable cookie store when available."""
    cookie_store = getattr(session.cookies.jar, "_cookies", None)
    if isinstance(cookie_store, dict):
        return cookie_store
    return {}


def update_session_cookie_store(
    session: requests.session.Session,
    cookies: Dict[str, Any],
) -> None:
    """Merge cached Yahoo cookies into the active session store."""
    cookie_store = getattr(session.cookies.jar, "_cookies", None)
    if isinstance(cookie_store, dict):
        cookie_store.update(cookies)