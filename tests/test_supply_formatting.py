import pytest
from app.domain.title_normalizer import normalize_phone_title

def test_normalize_titles():
    assert normalize_phone_title("Смартфон Sаmsung Galaxy A25 5G 8/256 GB Black чер.") == "A25 black"
    assert normalize_phone_title("Смартфон Redmi 12 8/256 ГБ Blue син.") == "12 blue"
    assert normalize_phone_title("Смартфон Samsung Galaxy A15 8/256 GB White бел.") == "A15 white"
