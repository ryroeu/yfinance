"""Persistent Yahoo cookie cache helpers."""

import datetime
from typing import Any, Optional

from curl_cffi import requests

from .. import cache, utils
from .session import session_cookie_store, update_session_cookie_store


def save_cookie_curl_cffi(session: requests.session.Session) -> bool:
    """Persist Yahoo cookies from the active curl_cffi session."""
    cookies = session_cookie_store(session)
    if len(cookies) == 0:
        return False
    yh_domains = [key for key in cookies if "yahoo" in key]
    if len(yh_domains) > 1:
        yh_domains = [key for key in yh_domains if "consent" not in key]
    if len(yh_domains) > 1:
        utils.get_yf_logger().debug(
            "Multiple Yahoo cookies, not sure which to cache: %s",
            yh_domains,
        )
        return False
    if len(yh_domains) == 0:
        return False
    yh_domain = yh_domains[0]
    cache.get_cookie_cache().store("curlCffi", {yh_domain: cookies[yh_domain]})
    return True


def load_cookie_curl_cffi(
    session: requests.session.Session,
) -> tuple[bool, Optional[Any]]:
    """Load a cached Yahoo cookie into the active session when still valid."""
    cookie_dict = cache.get_cookie_cache().lookup("curlCffi")
    cookies = cookie_dict.get("cookie") if isinstance(cookie_dict, dict) else None
    if not isinstance(cookies, dict) or not cookies:
        return False, None

    _, domain_cookies = next(iter(cookies.items()))
    path_cookies = domain_cookies.get("/") if isinstance(domain_cookies, dict) else None
    cookie = path_cookies.get("A3") if isinstance(path_cookies, dict) else None
    expiry_ts = getattr(cookie, "expires", None) if cookie is not None else None
    if not isinstance(expiry_ts, (int, float)):
        return False, None

    if expiry_ts > 2e9:
        expiry_ts //= 1e3
    expiry_dt = datetime.datetime.fromtimestamp(expiry_ts, tz=datetime.timezone.utc)
    if expiry_dt < datetime.datetime.now(datetime.timezone.utc):
        utils.get_yf_logger().debug("cached cookie expired")
        return False, None

    update_session_cookie_store(session, cookies)
    return True, cookie
