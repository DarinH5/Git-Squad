import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scoring import score_product, extract_price, extract_rating, extract_review_count


def test_product_score_is_bounded_and_explainable():
    result = score_product(
        "Wireless headphones 4.6 out of 5, 2k reviews, $79.99",
        "https://www.bestbuy.com/site/example",
        "Customer reviews available",
    )
    assert 0 <= result["score"] <= 100
    assert result["label"] in {"High", "Medium", "Low"}
    assert result["reasons"]
    assert result["signals"]["price"] == 79.99


def test_parsers_handle_missing_signals():
    assert extract_price("No listed price") is None
    assert extract_rating("No rating") is None
    assert extract_review_count("No reviews") == 0
