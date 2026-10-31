import pytest

from postprocess import parse_model_json


@pytest.mark.parametrize("text,expected", [
    ('{"answer": "94", "files": ["a"]}', {"answer": "94", "files": ["a"]}),
    ('{"answer": "94"} I used {the datasheet}.', {"answer": "94"}),
    ('Sure: {"answer": "94", "x": {"y": 1}} done', {"answer": "94", "x": {"y": 1}}),
    ('{not json} {"answer": "5"}', {"answer": "5"}),
    ("garbage", {}),
    ("", {}),
    ("[1, 2]", {}),
])
def test_parse(text, expected):
    assert parse_model_json(text) == expected
