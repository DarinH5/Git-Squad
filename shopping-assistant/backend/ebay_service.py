
"""
eBay Browse API integration for ShopWise AI.

Supports:
- eBay OAuth client-credentials authentication
- Searching fixed-price eBay listings
- Mock product responses for local testing
- Normalizing eBay listings into ShopWise product format
"""

import os
import time
from typing import Optional

import requests


PRODUCTION_API = "https://api.ebay.com"
SANDBOX_API = "https://api.sandbox.ebay.com"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"

_token = None
_token_expires_at = 0


class EbayAPIError(RuntimeError):
    """A safe-to-display error from eBay authentication or search."""


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

def ebay_mock_enabled() -> bool:
    return os.getenv("EBAY_MOCK_MODE", "false").strip().lower() == "true"


def ebay_is_configured() -> bool:
    """Return True if mock mode or real eBay credentials are available."""
    return ebay_mock_enabled() or bool(
        os.getenv("EBAY_CLIENT_ID")
        and os.getenv("EBAY_CLIENT_SECRET")
    )


def _environment():
    value = os.getenv("EBAY_ENV", "production").strip().lower()
    return SANDBOX_API if value == "sandbox" else PRODUCTION_API


# ---------------------------------------------------------
# eBay Authentication
# ---------------------------------------------------------

def get_ebay_access_token() -> str:
    """Return a cached application token, refreshing it before expiry."""
    global _token, _token_expires_at

    client_id = os.getenv("EBAY_CLIENT_ID")
    client_secret = os.getenv("EBAY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise EbayAPIError(
            "eBay credentials are missing. Add EBAY_CLIENT_ID and "
            "EBAY_CLIENT_SECRET to the backend .env file."
        )

    if _token and time.time() < (_token_expires_at - 60):
        return _token

    token_url = f"{_environment()}/identity/v1/oauth2/token"

    try:
        response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "scope": OAUTH_SCOPE,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise EbayAPIError(
            f"Could not reach eBay's authentication service: {exc}"
        ) from exc

    if not response.ok:
        detail = response.text[:300].replace("\n", " ")
        raise EbayAPIError(
            f"eBay authentication failed ({response.status_code}). "
            f"Check the App ID, Cert ID, and environment. {detail}"
        )

    try:
        payload = response.json()
        _token = payload["access_token"]
        _token_expires_at = time.time() + int(
            payload.get("expires_in", 7200)
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise EbayAPIError(
            "eBay returned an invalid OAuth token response."
        ) from exc

    return _token


# ---------------------------------------------------------
# Product Helpers
# ---------------------------------------------------------

def _canonical_category(raw_categories) -> str:
    """Reduce eBay's detailed taxonomy to ShopWise categories."""
    names = []

    for item in raw_categories or []:
        if isinstance(item, dict) and item.get("categoryName"):
            names.append(str(item["categoryName"]).lower())

    text = " ".join(names)

    if any(word in text for word in (
        "shoe", "sneaker", "boot", "sandal", "footwear"
    )):
        return "footwear"

    if any(word in text for word in (
        "jacket", "coat", "outerwear", "vest"
    )):
        return "jackets"

    if any(word in text for word in ("backpack", "rucksack")):
        return "backpacks"

    if any(word in text for word in (
        "kitchen", "cookware", "coffee", "small appliance"
    )):
        return "kitchen"

    if any(word in text for word in (
        "electronics", "computer", "laptop", "cell phone",
        "camera", "audio", "video game", "headphone", "tablet"
    )):
        return "electronics"

    if any(word in text for word in (
        "clothing", "apparel", "shirt", "pants", "dress", "sweater"
    )):
        return "clothing"

    if any(word in text for word in (
        "home", "furniture", "decor", "bedding"
    )):
        return "home"

    if names:
        return names[-1].strip().lower()

    return "other"


def _brand_from_aspects(item) -> Optional[str]:
    for aspect in item.get("localizedAspects") or []:
        if not isinstance(aspect, dict):
            continue

        if str(aspect.get("name", "")).strip().lower() == "brand":
            value = aspect.get("value")

            if value:
                return str(value)

    return None


def normalize_ebay_item(item):
    """Convert an eBay listing into the ShopWise product format."""
    price_info = item.get("price") or {}
    image = item.get("image") or {}
    categories = item.get("categories") or []

    try:
        price = float(price_info.get("value"))
    except (TypeError, ValueError):
        price = None

    return {
        "external_id": item.get("itemId"),
        "source": "mock" if ebay_mock_enabled() else "ebay",
        "retailer": (
            "eBay (Mock)" if ebay_mock_enabled() else "eBay"
        ),
        "title": item.get("title", "Untitled product"),
        "description": item.get("shortDescription", ""),
        "category": _canonical_category(categories),
        "brand": _brand_from_aspects(item),
        "price": price,
        "rating": None,
        "image_url": image.get("imageUrl"),
        "product_url": item.get("itemWebUrl"),
    }


# ---------------------------------------------------------
# Mock eBay Response
# ---------------------------------------------------------

def get_mock_ebay_response():
    """Return sample data that imitates the eBay Browse API."""
    return {
        "itemSummaries": [
            {
                "itemId": "MOCK-001",
                "title": "Sony WH-1000XM5 Wireless Headphones",
                "shortDescription": "Wireless noise cancelling headphones.",
                "price": {"value": "299.99", "currency": "USD"},
                "image": {
                    "imageUrl": "https://placehold.co/400x400?text=Sony+Headphones"
                },
                "itemWebUrl": "https://example.com/mock/sony-headphones",
                "categories": [
                    {"categoryName": "Electronics"}
                ],
                "localizedAspects": [
                    {"name": "Brand", "value": "Sony"}
                ],
            },
            {
                "itemId": "MOCK-002",
                "title": "Apple AirPods Pro 2",
                "shortDescription": "Wireless earbuds with active noise cancellation.",
                "price": {"value": "189.99", "currency": "USD"},
                "image": {
                    "imageUrl": "https://placehold.co/400x400?text=AirPods"
                },
                "itemWebUrl": "https://example.com/mock/airpods",
                "categories": [
                    {"categoryName": "Electronics"}
                ],
                "localizedAspects": [
                    {"name": "Brand", "value": "Apple"}
                ],
            },
            {
                "itemId": "MOCK-003",
                "title": "Nike Air Max Running Shoes",
                "shortDescription": "Comfortable everyday running shoes.",
                "price": {"value": "119.99", "currency": "USD"},
                "image": {
                    "imageUrl": "https://placehold.co/400x400?text=Nike+Shoes"
                },
                "itemWebUrl": "https://example.com/mock/nike-shoes",
                "categories": [
                    {"categoryName": "Shoes"}
                ],
                "localizedAspects": [
                    {"name": "Brand", "value": "Nike"}
                ],
            },
            {
                "itemId": "MOCK-004",
                "title": "Logitech MX Master 3S Mouse",
                "shortDescription": "Wireless ergonomic computer mouse.",
                "price": {"value": "89.99", "currency": "USD"},
                "image": {
                    "imageUrl": "https://placehold.co/400x400?text=Logitech+Mouse"
                },
                "itemWebUrl": "https://example.com/mock/logitech-mouse",
                "categories": [
                    {"categoryName": "Computer Accessories"}
                ],
                "localizedAspects": [
                    {"name": "Brand", "value": "Logitech"}
                ],
            },
        ]
    }


# ---------------------------------------------------------
# Product Search
# ---------------------------------------------------------


def search_ebay_products(
    query,
    limit=12,
    min_price=None,
    max_price=None
):
    """
    Search eBay or return mock listings.

    Both modes return products normalized into the same
    ShopWise product format.
    """

    limit = min(max(int(limit), 1), 50)

    # Use mock data instead of making an API request.
    if ebay_mock_enabled():
        payload = get_mock_ebay_response()
    else:
        token = get_ebay_access_token()
        url = f"{_environment()}/buy/browse/v1/item_summary/search"

        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                },
                params={
                    "q": query,
                    "limit": limit,
                    "filter": "buyingOptions:{FIXED_PRICE}",
                },
                timeout=20,
            )
        except requests.RequestException as exc:
            raise EbayAPIError(
                f"Could not reach eBay search: {exc}"
            ) from exc

        if not response.ok:
            detail = response.text[:300].replace("\n", " ")
            raise EbayAPIError(
                f"eBay search failed ({response.status_code}): {detail}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise EbayAPIError(
                "eBay returned an invalid search response."
            ) from exc

    # Normalize both mock and real eBay listings.
    items = payload.get("itemSummaries") or []

    products = [
        normalize_ebay_item(item)
        for item in items
        if isinstance(item, dict) and item.get("itemId")
    ]

    # Apply price filters.
    if min_price is not None:
        products = [
            p for p in products
            if p["price"] is not None and p["price"] >= min_price
        ]

    if max_price is not None:
        products = [
            p for p in products
            if p["price"] is not None and p["price"] <= max_price
        ]

    return products[:limit]

