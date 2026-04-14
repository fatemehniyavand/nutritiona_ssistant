from src.application.services.food_resolver_service import FoodResolverService


def test_exact_match_for_apple():
    resolver = FoodResolverService()

    result = resolver.resolve("apple")

    assert result["matched"] is True
    assert result["matched_food"] == "apple"
    assert result["kcal_per_100g"] == 52
    assert result["confidence"] == "HIGH"


def test_exact_match_for_brown_rice():
    resolver = FoodResolverService()

    result = resolver.resolve("brown rice")

    assert result["matched"] is True
    assert result["matched_food"] == "brown rice"
    assert result["kcal_per_100g"] == 111
    assert result["confidence"] == "HIGH"


def test_alias_match_for_apples():
    resolver = FoodResolverService()

    result = resolver.resolve("apples")

    assert result["matched"] is True
    assert result["matched_food"] == "apple"
    assert result["confidence"] == "HIGH"


def test_alias_match_for_bananas():
    resolver = FoodResolverService()

    result = resolver.resolve("bananas")

    assert result["matched"] is True
    assert result["matched_food"] == "banana"
    assert result["confidence"] == "HIGH"


def test_alias_match_for_white_rice():
    resolver = FoodResolverService()

    result = resolver.resolve("white rice")

    assert result["matched"] is True
    assert result["matched_food"] == "rice"
    assert result["confidence"] == "HIGH"


def test_alias_match_for_chicken_breast():
    resolver = FoodResolverService()

    result = resolver.resolve("chicken breast")

    assert result["matched"] is True
    assert result["matched_food"] == "chicken"
    assert result["confidence"] == "HIGH"


def test_compact_match_for_brownrice():
    resolver = FoodResolverService()

    result = resolver.resolve("brownrice")

    assert result["matched"] is True
    assert result["matched_food"] == "brown rice"


def test_compact_match_for_grilledchicken():
    resolver = FoodResolverService()

    result = resolver.resolve("grilledchicken")

    assert result["matched"] is True
    assert result["matched_food"] == "grilled chicken"


def test_case_insensitive_match():
    resolver = FoodResolverService()

    result = resolver.resolve("APPLE")

    assert result["matched"] is True
    assert result["matched_food"] == "apple"


def test_hyphen_and_spacing_do_not_break_match():
    resolver = FoodResolverService()

    result = resolver.resolve("grilled-chicken")

    assert result["matched"] is True
    assert result["matched_food"] == "grilled chicken"


def test_typo_appl_matches_apple():
    resolver = FoodResolverService()

    result = resolver.resolve("appl")

    assert result["matched"] is True
    assert result["matched_food"] == "apple"
    assert result["confidence"] in {"MEDIUM", "HIGH"}


def test_typo_bananna_matches_banana():
    resolver = FoodResolverService()

    result = resolver.resolve("bananna")

    assert result["matched"] is True
    assert result["matched_food"] == "banana"
    assert result["confidence"] in {"MEDIUM", "HIGH"}


def test_typo_avocad_matches_avocado():
    resolver = FoodResolverService()

    result = resolver.resolve("avocad")

    assert result["matched"] is True
    assert result["matched_food"] == "avocado"
    assert result["confidence"] in {"MEDIUM", "HIGH"}


def test_typo_bred_matches_bread():
    resolver = FoodResolverService()

    result = resolver.resolve("bred")

    assert result["matched"] is True
    assert result["matched_food"] == "bread"
    assert result["confidence"] in {"MEDIUM", "HIGH"}


def test_unknown_food_returns_not_matched():
    resolver = FoodResolverService()

    result = resolver.resolve("dragonfruitpizza")

    assert result["matched"] is False
    assert result["matched_food"] is None
    assert result["confidence"] == "LOW"


def test_empty_food_returns_not_matched():
    resolver = FoodResolverService()

    result = resolver.resolve("")

    assert result["matched"] is False
    assert result["matched_food"] is None


def test_suggest_for_appl_contains_apple():
    resolver = FoodResolverService()

    suggestions = resolver.suggest("appl")

    assert "apple" in suggestions


def test_suggest_for_bananna_contains_banana():
    resolver = FoodResolverService()

    suggestions = resolver.suggest("bananna")

    assert "banana" in suggestions


def test_suggest_limit_is_respected():
    resolver = FoodResolverService()

    suggestions = resolver.suggest("a", limit=2)

    assert len(suggestions) <= 2


def test_suggestions_are_canonical_food_names():
    resolver = FoodResolverService()

    suggestions = resolver.suggest("brownrice")

    assert "brown rice" in suggestions
    assert "brownrice" not in suggestions


def test_resolve_returns_match_reason_and_source():
    resolver = FoodResolverService()

    result = resolver.resolve("apple")

    assert "match_reason" in result
    assert "match_source" in result
    assert result["match_source"] == "local_demo_db"