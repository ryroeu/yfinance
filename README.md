<img src="./doc/yfinance-gh-logo-dark.webp#gh-dark-mode-only" height="100">
<img src="./doc/yfinance-gh-logo-light.webp#gh-light-mode-only" height="100">

# Download market data from Yahoo! Finance's API

<a target="new" href="https://github.com/ryroeu/yfinance"><img border=0 src="https://img.shields.io/badge/python-3.14.3-blue.svg?style=flat" alt="Python version"></a>
<a target="new" href="https://github.com/ryroeu/yfinance"><img border=0 src="https://img.shields.io/github/stars/ryroeu/yfinance.svg?style=social&label=Star&maxAge=60" alt="Star this repo"></a>

**yfinance** offers a Pythonic way to fetch financial & market data from [Yahoo!Ⓡ finance](https://finance.yahoo.com).

---

> [!IMPORTANT]
> **Yahoo!, Y!Finance, and Yahoo! finance are registered trademarks of Yahoo, Inc.**
>
> yfinance is **not** affiliated, endorsed, or vetted by Yahoo, Inc. It's an open-source tool that uses Yahoo's publicly available APIs, and is intended for research and educational purposes.
>
> **You should refer to Yahoo!'s terms of use** ([here](https://policies.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.htm), [here](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html), and [here](https://policies.yahoo.com/us/en/yahoo/terms/index.htm)) **for details on your rights to use the actual data downloaded.
>
> Remember - the Yahoo! finance API is intended for personal use only.**

---

## Main components

- `Ticker`: single ticker data
- `Tickers`: multiple tickers' data
- `download`: download market data for multiple tickers
- `Market`: get information about a market
- `WebSocket` and `AsyncWebSocket`: live streaming data
- `Search`: quotes and news from search
- `Lookup`: ticker symbol lookup
- `Sector` and `Industry`: sector and industry information

## Installation

Clone the repository and install in editable mode:

``` {.sourceCode .bash}
$ git clone https://github.com/ryroeu/yfinance
$ cd yfinance
$ pip install -e .
```

---

![Star History Chart](https://api.star-history.com/svg?repos=ryroeu/yfinance)

---

### Legal Stuff

**yfinance** is distributed under the **Apache Software License**. See
the [LICENSE.txt](https://github.com/ryroeu/yfinance/blob/main/LICENSE.txt) file in the release for details.

AGAIN - yfinance is **not** affiliated, endorsed, or vetted by Yahoo, Inc. It's
an open-source tool that uses Yahoo's publicly available APIs, and is
intended for research and educational purposes. You should refer to Yahoo!'s terms of use
([here](https://policies.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.htm),
[here](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html), and
[here](https://policies.yahoo.com/us/en/yahoo/terms/index.htm)) for
details on your rights to use the actual data downloaded.
