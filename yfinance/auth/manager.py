"""Authentication mixin for Yahoo session, cookie, and crumb handling."""

import threading
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from curl_cffi import requests

from .. import utils
from ..exceptions import YFRateLimitError
from .cookie_store import load_cookie_curl_cffi, save_cookie_curl_cffi
from .session import (
    create_default_session,
    get_network_request_options,
    resolve_proxy_config,
    session_cookie_store,
    sync_session_proxy,
    update_session_cookie_store,
    validate_session,
)
from .strategies import (
    build_consent_form_data,
    build_consent_payload,
    extract_input_value,
    fetch_csrf_consent_page,
    is_consent_url,
    resolve_consent_action,
)


class YahooAuthMixin:
    """Provide Yahoo authentication state and cookie/crumb lifecycle methods."""

    def _init_auth(self, session=None) -> None:
        self._crumb: Optional[str] = None
        self._cookie: Any = None
        self._cookie_strategy = "basic"
        self._cookie_lock = threading.Lock()
        self._session_is_caching = False
        self._expire_after = None

        self._session: requests.session.Session = create_default_session()
        self._set_session(session or self._session)

    def _set_session(self, session):
        if session is None:
            return

        session_is_caching = validate_session(session)
        with self._cookie_lock:
            changed_session = session is not self._session
            self._session_is_caching = session_is_caching
            self._session = session
            self._sync_session_proxy()
            if changed_session:
                self._cookie = None
                self._crumb = None
                self._cookie_strategy = "basic"

    def _sync_session_proxy(self) -> None:
        sync_session_proxy(self._session)

    def _resolve_proxy_config(self) -> Any:
        return resolve_proxy_config()

    def _get_network_request_options(self) -> Dict[str, Any]:
        return get_network_request_options(self._session)

    def _session_cookie_store(self) -> Dict[str, Any]:
        return session_cookie_store(self._session)

    def _update_session_cookie_store(self, cookies: Dict[str, Any]) -> None:
        update_session_cookie_store(self._session, cookies)

    def _set_cookie_strategy(self, strategy, have_lock=False):
        if strategy == self._cookie_strategy:
            return
        if have_lock:
            self._set_cookie_strategy_locked()
            return
        with self._cookie_lock:
            self._set_cookie_strategy_locked()

    def _set_cookie_strategy_locked(self):
        if self._cookie_strategy == "csrf":
            utils.get_yf_logger().debug(
                "toggling cookie strategy %s -> basic",
                self._cookie_strategy,
            )
            self._session.cookies.clear()
            self._cookie_strategy = "basic"
        else:
            utils.get_yf_logger().debug(
                "toggling cookie strategy %s -> csrf",
                self._cookie_strategy,
            )
            self._cookie_strategy = "csrf"
        self._cookie = None
        self._crumb = None

    @utils.log_indent_decorator
    def _save_cookie_curl_cffi(self):
        return save_cookie_curl_cffi(self._session)

    @utils.log_indent_decorator
    def _load_cookie_curl_cffi(self):
        loaded, cookie = load_cookie_curl_cffi(self._session)
        if loaded:
            self._cookie = cookie
        return loaded

    @utils.log_indent_decorator
    def _get_cookie_basic(self, timeout=30):
        if self._cookie is not None:
            utils.get_yf_logger().debug("reusing cookie")
            return True
        if self._load_cookie_curl_cffi():
            utils.get_yf_logger().debug("reusing persistent cookie")
            return True

        try:
            self._session.get(
                url="https://fc.yahoo.com",
                timeout=timeout,
                allow_redirects=True,
                **self._get_network_request_options(),
            )
        except requests.exceptions.RequestException as error:
            utils.get_yf_logger().debug(
                "Handling cookie fetch error in basic strategy: %s",
                error,
            )
            return False
        self._save_cookie_curl_cffi()
        return True

    @utils.log_indent_decorator
    def _get_crumb_basic(self, timeout=30):
        if self._crumb is not None:
            utils.get_yf_logger().debug("reusing crumb")
            return self._crumb

        if not self._get_cookie_basic(timeout):
            return None

        get_args = {
            "url": "https://query1.finance.yahoo.com/v1/test/getcrumb",
            "timeout": timeout,
            "allow_redirects": True,
        }
        if self._session_is_caching and self._expire_after is not None:
            get_args["expire_after"] = self._expire_after
        get_args.update(self._get_network_request_options())
        crumb_response = self._session.get(**get_args)
        self._crumb = crumb_response.text
        if crumb_response.status_code >= 400:
            utils.get_yf_logger().debug(
                "Didn't receive crumb because response code=%s body=%s",
                crumb_response.status_code,
                self._crumb,
            )
            self._crumb = None
            if crumb_response.status_code == 429:
                raise YFRateLimitError()
            return None
        if crumb_response.status_code == 429 or "Too Many Requests" in self._crumb:
            utils.get_yf_logger().debug("Didn't receive crumb %s", self._crumb)
            self._crumb = None
            raise YFRateLimitError()

        if self._crumb is None or "<html>" in self._crumb:
            utils.get_yf_logger().debug("Didn't receive crumb")
            self._crumb = None
            return None

        utils.get_yf_logger().debug("crumb = '%s'", self._crumb)
        return self._crumb

    @utils.log_indent_decorator
    def _get_cookie_and_crumb_basic(self, timeout):
        if not self._get_cookie_basic(timeout):
            return None
        return self._get_crumb_basic(timeout)

    def _extract_input_value(self, soup, input_name: str) -> Optional[str]:
        return extract_input_value(soup, input_name)

    def _fetch_csrf_consent_page(self, base_args):
        return fetch_csrf_consent_page(
            self._session,
            base_args,
            self._get_network_request_options(),
            session_is_caching=self._session_is_caching,
            expire_after=self._expire_after,
        )

    @utils.log_indent_decorator
    def _get_cookie_csrf(self, timeout):
        if self._cookie is not None:
            utils.get_yf_logger().debug("reusing cookie")
            return True

        if self._load_cookie_curl_cffi():
            utils.get_yf_logger().debug("reusing persistent cookie")
            self._cookie = True
            return True

        base_args = {"timeout": timeout}
        response = self._fetch_csrf_consent_page(base_args)
        if response is None:
            return False

        soup = BeautifulSoup(response.content, "html.parser")
        csrf_token = self._extract_input_value(soup, "csrfToken")
        session_id = self._extract_input_value(soup, "sessionId")
        if csrf_token is None or session_id is None:
            return False
        utils.get_yf_logger().debug("csrfToken = %s", csrf_token)
        utils.get_yf_logger().debug("sessionId = %s", session_id)

        data = build_consent_payload(session_id, csrf_token)
        post_args = {
            **base_args,
            "url": f"https://consent.yahoo.com/v2/collectConsent?sessionId={session_id}",
            "data": data,
        }
        get_args = {
            **base_args,
            "url": f"https://guce.yahoo.com/copyConsent?sessionId={session_id}",
            "data": data,
        }
        try:
            if self._session_is_caching and self._expire_after is not None:
                post_args["expire_after"] = self._expire_after
                get_args["expire_after"] = self._expire_after
            post_args.update(self._get_network_request_options())
            self._session.post(**post_args)
            get_args.update(self._get_network_request_options())
            self._session.get(**get_args)
        except requests.exceptions.ChunkedEncodingError:
            utils.get_yf_logger().debug(
                "_get_cookie_csrf() encountering requests.exceptions.ChunkedEncodingError, aborting"
            )
        self._cookie = True
        self._save_cookie_curl_cffi()
        return True

    @utils.log_indent_decorator
    def _get_crumb_csrf(self, timeout=30):
        if self._crumb is not None:
            utils.get_yf_logger().debug("reusing crumb")
            return self._crumb

        if not self._get_cookie_csrf(timeout):
            return None

        get_args = {
            "url": "https://query2.finance.yahoo.com/v1/test/getcrumb",
            "timeout": timeout,
        }
        if self._session_is_caching and self._expire_after is not None:
            get_args["expire_after"] = self._expire_after
        get_args.update(self._get_network_request_options())
        response = self._session.get(**get_args)
        self._crumb = response.text

        if response.status_code >= 400:
            utils.get_yf_logger().debug(
                "Didn't receive crumb because response code=%s body=%s",
                response.status_code,
                self._crumb,
            )
            self._crumb = None
            if response.status_code == 429:
                raise YFRateLimitError()
            return None

        if response.status_code == 429 or "Too Many Requests" in self._crumb:
            utils.get_yf_logger().debug("Didn't receive crumb %s", self._crumb)
            self._crumb = None
            raise YFRateLimitError()

        if self._crumb is None or "<html>" in self._crumb or self._crumb == "":
            utils.get_yf_logger().debug("Didn't receive crumb")
            self._crumb = None
            return None

        utils.get_yf_logger().debug("crumb = '%s'", self._crumb)
        return self._crumb

    @utils.log_indent_decorator
    def _get_cookie_and_crumb(self, timeout=30):
        crumb, strategy = None, None

        utils.get_yf_logger().debug("cookie_mode = '%s'", self._cookie_strategy)

        with self._cookie_lock:
            if self._cookie_strategy == "csrf":
                crumb = self._get_crumb_csrf()
                if crumb is None:
                    self._set_cookie_strategy("basic", have_lock=True)
                    crumb = self._get_cookie_and_crumb_basic(timeout)
            else:
                crumb = self._get_cookie_and_crumb_basic(timeout)
                if crumb is None:
                    self._set_cookie_strategy("csrf", have_lock=True)
                    crumb = self._get_crumb_csrf()
            strategy = self._cookie_strategy
        return crumb, strategy

    def _is_this_consent_url(self, response_url: str) -> bool:
        return is_consent_url(response_url)

    def _build_consent_form_data(self, form) -> Dict[str, str]:
        return build_consent_form_data(form)

    def _accept_consent_form(self, consent_resp: requests.Response, timeout: int):
        soup = BeautifulSoup(consent_resp.text, "html.parser")
        form = soup.find("form")
        if not form:
            return consent_resp

        action = resolve_consent_action(consent_resp.url, form)
        data = self._build_consent_form_data(form)
        headers = {"Referer": consent_resp.url}
        return self._session.post(
            action,
            data=data,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            **self._get_network_request_options(),
        )