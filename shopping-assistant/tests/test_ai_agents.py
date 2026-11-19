import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from ai import interpret_intent, ShoppingAgent


def test_intent_extracts_upper_budget():
    result = interpret_intent("Find wireless earbuds under $100", ["electronics"])
    assert result["max_price"] == 100
    assert "earbuds" in result["keywords"].lower()
    assert result["min_price"] is None


def test_intent_extracts_price_range():
    result = interpret_intent("laptop between 500 and 900", ["electronics"])
    assert result["min_price"] == 500
    assert result["max_price"] == 900


def test_agent_orchestrates_profile_search_and_ranking():
    calls = {}
    def profile(user_id):
        calls["user_id"] = user_id
        return {"preferred_brands": ["Acme"]}
    def search_fn(**kwargs):
        calls["search"] = kwargs
        return {"results": [{"id": 1, "brand": "Acme"}]}
    def rank(products, user_profile):
        calls["profile"] = user_profile
        return products
    result = ShoppingAgent(search_fn, profile, rank).run(
        "Acme earbuds under $80", 7, ["electronics"]
    )
    assert calls["user_id"] == 7
    assert calls["search"]["max_price"] == 80
    assert len(result["agents"]) == 4
    assert result["results"][0]["id"] == 1
