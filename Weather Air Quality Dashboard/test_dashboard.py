
import pytest

from weather_dashboard import (
    validate_city,
    aqi_category,
    describe_weather,
)


def test_validate_city_trims_spaces():
    assert validate_city("  Vijayawada  ") == "Vijayawada"


def test_validate_city_rejects_empty():
    with pytest.raises(ValueError):
        validate_city("   ")


def test_validate_city_rejects_long():
    with pytest.raises(ValueError):
        validate_city("x" * 101)


def test_aqi_category_good():
    category, _ = aqi_category(30)
    assert category == "Good"


def test_aqi_category_unavailable():
    category, _ = aqi_category(None)
    assert category == "Unavailable"


def test_describe_weather_known():
    assert describe_weather(0) == "Clear sky"


def test_describe_weather_unknown():
    assert describe_weather(9999) == "Unknown"
