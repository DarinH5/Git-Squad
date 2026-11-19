"""Embedded shopping-agent workflow.

The app deliberately uses deterministic local parsing as a reliable baseline.
An optional LLM can enrich intent extraction, but is never required for core search.
"""
from __future__ import annotations

import re
from typing import Any


def interpret_intent(query: str, categories: list[str] | None = None) -> dict[str, Any]:
    """Extract product keywords and common budget constraints without an LLM."""
    text = (query or "").strip()
    categories = categories or []
    low = high = None
    cleaned = text

    def take(pattern: str):
        nonlocal cleaned
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            cleaned = cleaned[:match.start()] + " " + cleaned[match.end():]
        return match

    number = r"\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)"
    match = take(rf"\bbetween\s+{number}\s+(?:and|to|-)\s*{number}")
    if match:
        low, high = sorted((float(match.group(1).replace(",", "")),
                            float(match.group(2).replace(",", ""))))
    else:
        match = take(rf"\b(?:under|below|less than|up to|at most|max(?:imum)?)\s*{number}")
        if match:
            high = float(match.group(1).replace(",", ""))
        match = take(rf"\b(?:over|above|more than|at least|min(?:imum)?)\s*{number}")
        if match:
            low = float(match.group(1).replace(",", ""))

    category = None
    lowered = cleaned.casefold()
    for candidate in sorted(categories, key=len, reverse=True):
        if candidate and candidate.casefold() in lowered:
            category = candidate
            cleaned = re.sub(re.escape(candidate), " ", cleaned, flags=re.IGNORECASE)
            break

    filler = {"find", "show", "get", "buy", "want", "need", "looking", "for",
              "me", "some", "best", "good", "please", "recommend", "recommendations"}
    keywords = " ".join(w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", cleaned)
                        if w.casefold() not in filler).strip()
    return {
        "keywords": keywords or text,
        "min_price": low,
        "max_price": high,
        "category": category,
        "explanation": "I translated your request into product keywords and budget filters.",
    }


class ShoppingAgent:
    """Small orchestrator for intent, catalog retrieval, and personalization."""

    def __init__(self, search_fn, profile_fn, rank_fn):
        self.search_fn = search_fn
        self.profile_fn = profile_fn
        self.rank_fn = rank_fn

    def run(self, query: str, user_id: int, categories: list[str], limit: int = 12):
        intent = interpret_intent(query, categories)
        profile = self.profile_fn(user_id)
        results = self.search_fn(
            q=intent["keywords"],
            min_price=intent["min_price"],
            max_price=intent["max_price"],
            category=intent["category"],
            limit=limit,
        )
        products = self.rank_fn(results.get("results", []), profile)
        return {
            "query": query,
            "interpretation": intent["explanation"],
            "applied": {k: intent[k] for k in ("keywords", "min_price", "max_price", "category")},
            "personalized": bool(profile),
            "agents": [
                {"name": "Intent Agent", "status": "complete", "task": "Parsed product intent and budget."},
                {"name": "Profile Agent", "status": "complete", "task": "Loaded saved shopping preferences."},
                {"name": "Product Research Agent", "status": "complete", "task": "Searched the product catalog."},
                {"name": "Ranking Agent", "status": "complete", "task": "Applied explainable recommendation signals."},
            ],
            "results": products,
        }
