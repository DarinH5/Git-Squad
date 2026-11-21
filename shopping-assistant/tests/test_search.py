from backend.main import parse_search


def test_search_under_budget():
    words, shown, minimum, maximum = parse_search("boots under $100")

    assert words == ["boot"]
    assert shown == ["boots"]
    assert minimum is None
    assert maximum == 100.0


def test_search_between_prices():
    words, shown, minimum, maximum = parse_search(
        "jackets between $50 and $100"
    )

    assert words == ["jacket"]
    assert shown == ["jackets"]
    assert minimum == 50.0
    assert maximum == 100.0


def test_search_preserves_product_numbers():
    words, shown, minimum, maximum = parse_search("40L backpack")

    assert words == ["40L", "backpack"]
    assert shown == ["40L", "backpack"]
    assert minimum is None
    assert maximum is None
