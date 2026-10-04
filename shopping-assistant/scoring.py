"""Product quality score (0-100).

This is a transparent *heuristic* computed from what a web-search result
exposes (domain, URL scheme, and rating/review/price text in the snippet).
It is not a verified product rating. Swap in a real ratings API later by
replacing `score_product`; the return shape is what the UI relies on.

Breakdown (max points):
    source trust 45 | rating 25 | review volume 15 | https 10 | price shown 5
    minus up to 30 for scam/counterfeit red flags.
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
_REVIEW_COUNT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?([kK])?\s*(?:customer\s+)?(?:reviews?|ratings?)")
_PRICE = re.compile(r"\$\s?\d")


def _host(url: str) -> str:
    host = (urlparse(url).netloc or "").lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _matches(host: str, domains) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def _extract_rating(text: str):
    for pattern in _RATING_PATTERNS:
        for match in pattern.finditer(text):
            value = float(match.group(1))
            if 0 < value <= 5:
                return value
    return None


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


def score_product(title: str, url: str, body: str) -> dict:
    text = f"{title} {body}"
    lowered = text.lower()
    host = _host(url)
    is_https = url.lower().startswith("https://")
    reasons = []

    # Source trust (0-45)
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

    # Rating (0-25)
    rating = _extract_rating(text)
    if rating is not None:
        rating_pts = round(rating / 5 * 25)
        reasons.append(f"Listed rating of {rating:g}/5")
    else:
        rating_pts = 0
        reasons.append("No rating found in the listing")

    # Review volume (0-15), log scale: ~10,000 reviews = full marks
    count = _extract_review_count(text)
    review_pts = min(15, round(15 * math.log10(count + 1) / 4)) if count else 0
    if count:
        reasons.append(f"About {count:,} reviews mentioned")

    # HTTPS (0-10) and price (0-5)
    https_pts = 10 if is_https else 0
    if not is_https:
        reasons.append("Link is not HTTPS")
    price_pts = 5 if _PRICE.search(text) else 0

    # Red flags (up to -30)
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
    }
