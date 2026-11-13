from backend.main import personalize_products


def make_product(brand="TrailCo", category="footwear",
                 price=80, rating=4.5, retailer=""):
    return {
        "title": "Waterproof Hiking Boots",
        "description": "Boots for hiking",
        "brand": brand,
        "category": category,
        "price": price,
        "rating": rating,
        "retailer": retailer,
    }


def test_preferred_brand_increases_score():
    product = make_product()
    result = personalize_products(
        [product], {"preferred_brands": ["trailco"]}
    )

    assert result[0]["personalization_score"] == 15
    assert "From one of your preferred brands" in result[0]["personalization_reasons"]


def test_preferred_category_increases_score():
    result = personalize_products(
        [make_product()], {"preferred_categories": ["FOOTWEAR"]}
    )

    assert result[0]["personalization_score"] == 12


def test_avoided_brand_reduces_score():
    result = personalize_products(
        [make_product()], {"avoided_brands": ["TrailCo"]}
    )

    assert result[0]["personalization_score"] == -25
    assert result[0]["recommendation_score"] == 20


def test_preferred_retailer_matches_domain():
    result = personalize_products(
        [make_product(retailer="shop.example.com")],
        {"preferred_retailers": ["example.com"]}
    )

    assert result[0]["personalization_score"] == 8


def test_product_within_budget():
    result = personalize_products(
        [make_product(price=80)], {"budget_max": 100}
    )

    assert result[0]["personalization_score"] == 8


def test_product_above_budget():
    result = personalize_products(
        [make_product(price=150)], {"budget_max": 100}
    )

    assert result[0]["personalization_score"] == -12


def test_matching_interests():
    result = personalize_products(
        [make_product()], {"interests": "hiking"}
    )

    assert result[0]["personalization_score"] == 2


def test_preferred_brand_ranks_first():
    products = [
        make_product(brand="OtherBrand", rating=4.8),
        make_product(brand="TrailCo", rating=4.0),
    ]

    result = personalize_products(
        products, {"preferred_brands": ["TrailCo"]}
    )

    assert result[0]["brand"] == "TrailCo"
    assert result[0]["personalization_score"] == 15
