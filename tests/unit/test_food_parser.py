from src.application.services.nlu.food_parser import FoodParser
from src.application.services.nlu.food_normalizer import FoodNormalizer


def setup_parser():
    return FoodParser(), FoodNormalizer()


def test_single_item_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("apple 200g")

    items = parser.parse(text)

    assert len(items) == 1
    assert items[0].food_name == "apple"
    assert items[0].grams == 200.0


def test_compact_input_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("apple200g")

    items = parser.parse(text)

    assert len(items) == 1
    assert items[0].food_name == "apple"
    assert items[0].grams == 200.0


def test_two_items_with_and():
    parser, norm = setup_parser()
    text = norm.normalize("apple 200g and banana 100g")

    items = parser.parse(text)

    assert len(items) == 2

    assert items[0].food_name == "apple"
    assert items[0].grams == 200.0

    assert items[1].food_name == "banana"
    assert items[1].grams == 100.0


def test_two_items_without_and():
    parser, norm = setup_parser()
    text = norm.normalize("apple 200g banana 100g")

    items = parser.parse(text)

    assert len(items) == 2


def test_multiple_items_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("apple 200g banana 100g milk 200g")

    items = parser.parse(text)

    assert len(items) == 3


def test_plus_connector_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("milk 200g plus oats 40g")

    items = parser.parse(text)

    assert len(items) == 2

    assert items[1].food_name == "oats"
    assert items[1].grams == 40.0


def test_with_connector_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("rice 150g with milk 200g")

    items = parser.parse(text)

    assert len(items) == 2


def test_add_connector_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("add apple 200g")

    items = parser.parse(text)

    assert len(items) == 1
    assert items[0].food_name == "apple"


def test_invalid_text_returns_empty():
    parser, norm = setup_parser()
    text = norm.normalize("hello world")

    items = parser.parse(text)

    assert items == []


def test_partial_parse_when_noise_present():
    parser, norm = setup_parser()
    text = norm.normalize("hello apple 200g xyz")

    items = parser.parse(text)

    assert len(items) == 1
    assert items[0].food_name == "apple"


def test_float_grams_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("milk 200.5g")

    items = parser.parse(text)

    assert len(items) == 1
    assert items[0].grams == 200.5


def test_reject_food_without_grams():
    parser, norm = setup_parser()
    text = norm.normalize("apple banana")

    items = parser.parse(text)

    assert items == []


def test_reject_quantity_without_food():
    parser, norm = setup_parser()
    text = norm.normalize("200g")

    items = parser.parse(text)

    assert items == []


def test_compact_multi_items():
    parser, norm = setup_parser()
    text = norm.normalize("apple200grice150g")

    items = parser.parse(text)

    assert len(items) == 2


def test_brownrice_alias_parsing():
    parser, norm = setup_parser()
    text = norm.normalize("brownrice150g")

    items = parser.parse(text)

    assert len(items) == 1
    assert items[0].food_name == "brownrice"