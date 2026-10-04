"""Transparent 0-100 product quality/reliability heuristic.

The score is based only on information visible in a search result. It is NOT a
verified product-quality guarantee. A structured shopping API can replace the
parsers later without changing the response shape used by the UI.
"""
import math
import re
from urllib.parse import urlparse

TRUSTED_RETAILERS = {
    "amazon.com", "bestbuy.com", "walmart.com", "target.com", "costco.com",
    "newegg.com", "homedepot.com", "lowes.com", "apple.com", "bhphotovideo.com",
    "microcenter.com", "samsung.com", "dell.com", "hp.com", "lenovo.com",
    "nike.com", "adidas.com", "rei.com", "ebay.com", "macys.com",
}
REVIEW_SITES = {
    "wirecutter.com", "nytimes.com", "rtings.com", "consumerreports.org",
    "pcmag.com", "cnet.com", "tomsguide.com", "techradar.com", "pcworld.com",
}
SUSPICIOUS_TLDS = (".xyz", ".top", ".click", ".buzz", ".icu", ".rest", ".monster")
RED_FLAGS = (
    "replica", "counterfeit", "knockoff", "knock-off", "fake", "scam",
    "too good to be true", "dropship",
)

_RATING_PATTERNS = (
    re.compile(r"(\d(?:\.\d)?)\s*(?:out of|/)\s*5", re.I),
    re.compile(r"(\d(?:\.\d)?)\s*(?:stars?|★)", re.I),
)
_REVIEW_COUNT = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s?([kK])?\s*(?:customer\s+)?(?:reviews?|ratings?)"
)
_PRICE = re.compile(r"\$\s?([0-9][0-9,]*(?:\.\d{1,2})?)")


def host_from_url(url: str) -> str:
    host = (urlparse(url).netloc or "").lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _matches(host: str, domains) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def extract_price(text: str):
    values = []
    for match in _PRICE.finditer(text):
        try:
            values.append(float(match.group(1).replace(",", "")))
        except ValueError:
            pass
    return min(values) if values else None


def _extract_rating(text: str):
    for pattern in _RATING_PATTERNS:
        for match in pattern.finditer(text):
            value = float(match.group(1))
            if 0 < value <= 5:
                return value
    return None


def extract_rating(text: str):
    return _extract_rating(text)


def _extract_review_count(text: str) -> int:
    best = 0
    for match in _REVIEW_COUNT.finditer(text):
        try:
            number = float(match.group(1).replace(",", ""))
        except ValueError:
            continue
        if match.group(2):
            number *= 1000
        best = max(best, int(number))
    return best


def extract_review_count(text: str) -> int:
    return _extract_review_count(text)


def score_product(title: str, url: str, body: str) -> dict:
    text = f"{title} {body}"
    lowered = text.lower()
    host = host_from_url(url)
    is_https = url.lower().startswith("https://")
    reasons = []

    if _matches(host, TRUSTED_RETAILERS):
        trust = 45
        reasons.append(f"Sold by a well-known retailer ({host})")
    elif _matches(host, REVIEW_SITES):
        trust = 35
        reasons.append(f"Published by an established review site ({host})")
    elif host.endswith(SUSPICIOUS_TLDS):
        trust = 5
        reasons.append(f"Unfamiliar, frequently abused domain type ({host})")
    else:
        trust = 20 if is_https else 8
        reasons.append(f"Unrecognized seller ({host or 'unknown'}); verify before buying")

    rating = _extract_rating(text)
    if rating is not None:
        rating_pts = round(rating / 5 * 25)
        reasons.append(f"Listed rating of {rating:g}/5")
    else:
        rating_pts = 0
        reasons.append("No rating found in the listing")

    count = _extract_review_count(text)
    review_pts = min(15, round(15 * math.log10(count + 1) / 4)) if count else 0
    if count:
        reasons.append(f"About {count:,} reviews mentioned")

    https_pts = 10 if is_https else 0
    if not is_https:
        reasons.append("Link is not HTTPS")

    price = extract_price(text)
    price_pts = 5 if price is not None else 0
    if price is not None:
        reasons.append(f"Price information found (${price:,.2f})")

    flags = [flag for flag in RED_FLAGS if flag in lowered]
    penalty = min(30, 15 * len(flags))
    if flags:
        reasons.append("Warning words found: " + ", ".join(flags))

    total = trust + rating_pts + review_pts + https_pts + price_pts - penalty
    score = max(0, min(100, total))
    label = "High" if score >= 75 else "Medium" if score >= 50 else "Low"

    return {
        "score": score,
        "label": label,
        "reasons": reasons,
        "breakdown": {
            "source_trust": trust,
            "rating": rating_pts,
            "review_volume": review_pts,
            "https": https_pts,
            "price_shown": price_pts,
            "penalty": -penalty,
        },
        "signals": {
            "retailer": host,
            "price": price,
            "rating": rating,
            "review_count": count,
        },
    }
