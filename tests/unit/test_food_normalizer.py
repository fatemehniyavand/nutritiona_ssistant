from src.application.services.nlu.food_normalizer import FoodNormalizer


def test_empty_string_returns_empty():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("") == ""


def test_whitespace_only_returns_empty():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("   ") == ""


def test_apple200g_is_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("apple200g") == "apple 200g"


def test_addbanana100g_is_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("addbanana100g") == "add banana 100g"


def test_rice100gandmilk200g_is_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("rice100gandmilk200g") == "rice 100g and milk 200g"


def test_apple_200_grams_is_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("apple 200 grams") == "apple 200g"


def test_apple_200_g_is_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("apple 200 g") == "apple 200g"


def test_punctuation_separators_are_removed():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("apple,200g;banana/100g") == "apple 200g banana 100g"


def test_hyphenated_food_spacing_is_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("chicken- breast 150 g") == "chicken-breast 150g"


def test_uppercase_input_is_lowercased_and_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("APPLE200G") == "apple 200g"


def test_compact_brownrice_is_preserved_for_alias_resolution():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("brownrice150g") == "brownrice 150g"


def test_grilledchicken200g_is_normalized():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("grilledchicken200g") == "grilledchicken 200g"


def test_multiple_spaces_are_collapsed():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("apple    200     g") == "apple 200g"


def test_noise_symbols_are_removed_but_food_text_is_kept():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("apple@@@200g") == "apple 200g"


def test_apple200grice150g_is_split_into_separable_tokens():
    normalizer = FoodNormalizer()
    assert normalizer.normalize("apple200grice150g") == "apple 200g rice 150g"