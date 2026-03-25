"""Helpers for Yahoo authentication strategies and consent handling."""

from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from curl_cffi import requests

from .. import utils


def extract_input_value(soup: BeautifulSoup, input_name: str) -> Optional[str]:
    """Extract a named input field from a consent form page."""
    input_tag = soup.find("input", attrs={"name": input_name})
    if input_tag is None:
        utils.get_yf_logger().debug('Failed to find "%s" in response', input_name)
        return None
    input_value = input_tag.get("value")
    if not isinstance(input_value, str):
        utils.get_yf_logger().debug(
            'Failed to parse "%s" value in response',
            input_name,
        )
        return None
    return input_value


def fetch_csrf_consent_page(
    session: requests.session.Session,
    base_args: Dict[str, Any],
    request_options: Dict[str, Any],
    *,
    session_is_caching: bool,
    expire_after: Any,
):
    """Fetch Yahoo's consent page for the CSRF cookie strategy."""
    request_args = {**base_args, "url": "https://guce.yahoo.com/consent"}
    try:
        if session_is_caching and expire_after is not None:
            request_args["expire_after"] = expire_after
        request_args.update(request_options)
        return session.get(**request_args)
    except requests.exceptions.ChunkedEncodingError:
        utils.get_yf_logger().debug(
            "_get_cookie_csrf() encountering requests.exceptions.ChunkedEncodingError, aborting"
        )
        return None


def build_consent_payload(session_id: str, csrf_token: str) -> Dict[str, Any]:
    """Return the form payload Yahoo expects for consent acceptance."""
    return {
        "agree": ["agree", "agree"],
        "consentUUID": "default",
        "sessionId": session_id,
        "csrfToken": csrf_token,
        "originalDoneUrl": "https://finance.yahoo.com/",
        "namespace": "yahoo",
    }


def build_consent_form_data(form) -> Dict[str, str]:
    """Build a generic form payload from Yahoo consent markup."""
    payload: Dict[str, str] = {}
    for input_tag in form.find_all("input"):
        name_attr = input_tag.get("name")
        if not isinstance(name_attr, str) or name_attr == "":
            continue

        input_type = input_tag.get("type")
        normalized_type = input_type.lower() if isinstance(input_type, str) else "text"
        value_attr = input_tag.get("value")
        value = value_attr if isinstance(value_attr, str) else ""
        if normalized_type in ("checkbox", "radio"):
            name_lower = name_attr.lower()
            has_agree_name = "agree" in name_lower or "accept" in name_lower
            if has_agree_name or input_tag.has_attr("checked"):
                payload[name_attr] = value if value != "" else "1"
        else:
            payload[name_attr] = value

    lowered = {key.lower() for key in payload}
    if not any("agree" in key or "accept" in key for key in lowered):
        payload["agree"] = "1"
    return payload


def is_consent_url(response_url: str) -> bool:
    """Return whether a response URL points at Yahoo's consent flow."""
    try:
        hostname = urlsplit(response_url).hostname
        return bool(hostname and hostname.endswith("consent.yahoo.com"))
    except (AttributeError, TypeError, ValueError):
        return False


def resolve_consent_action(consent_url: str, form) -> str:
    """Resolve the POST target for a Yahoo consent form."""
    action_attr = form.get("action")
    if isinstance(action_attr, str) and action_attr != "":
        return urljoin(consent_url, action_attr)
    return consent_url
