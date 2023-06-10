import sys
from random import randint

import pytest

from tests.datastructures import (
    CRequestProxy,
    CustomResponse,
    CYahooAPI,
    StandardStockInfo,
    StandardStockInfoValues,
)
from tests.helpers import exception_tester


def test_get_data_pass():
    num = randint(1, 100)
    api = CYahooAPI(response=CustomResponse())
    assert api.get_data(["FI"]) == [StandardStockInfo]

    response = CustomResponse(result_num=num)
    api = CYahooAPI(response=response)
    assert api.get_data(["FI"] * num) == [StandardStockInfo] * num

    # Incomplete pass, some pass some fails
    response_data = CustomResponse().json()
    result_data = CustomResponse().default_data()
    good_results = [result_data] * 10
    bad_result_data = [CustomResponse().default_data()] * 4
    del bad_result_data[0]["symbol"]
    del bad_result_data[1]["marketCap"]
    del bad_result_data[2]["regularMarketPrice"]
    del bad_result_data[3]["regularMarketVolume"]

    response_data["quoteResponse"]["result"] = good_results + bad_result_data
    api = CYahooAPI(response=CustomResponse(replace_json=response_data))
    assert api.get_data(["FI"] * 14) == [StandardStockInfo] * 10 + [None] * 4


def get_test_data_incomplete():
    responses = [CustomResponse().default_data()] * 9
    remove_keys = [
        "symbol",
        "marketCap",
        "regularMarketPrice",
        "regularMarketVolume",
        "regularMarketDayHigh",
        "regularMarketDayLow",
        "regularMarketOpen",
        "regularMarketPreviousClose",
        "regularMarketTime",
    ]
    for response, key in zip(responses, remove_keys):
        del response[key]

    for response in responses:
        num = randint(1, 100)
        api = CYahooAPI(
            response=CustomResponse(replace_result=[response], result_num=num)
        )
        assert api.get_data(["FI"] * num) == [None] * num

    # test names incompleteness, fallback and complete absence seperately
    responses = [CustomResponse().default_data()] * 3
    keys = ["shortName", "displayName"]

    # should use longName by default
    for response, key in zip(responses, keys):
        del response[key]
        num = randint(1, 100)
        api = CYahooAPI(
            response=CustomResponse(replace_result=[response], result_num=num)
        )
        assert api.get_data(["FI"] * num) == [StandardStockInfo] * num

    # should use shortName if longName is absent
    response = CustomResponse().default_data()
    del response["longName"]
    response["shortName"] = "myShortName123"
    response["displayName"] = "myDisplayName123"

    api = CYahooAPI(response=CustomResponse(replace_result=[response]))
    expected = dict(**StandardStockInfoValues)
    expected["name"] = response["shortName"]
    assert api.get_data(["FI"]) == [StandardStockInfo(**expected)]

    del response["shortName"]
    api = CYahooAPI(response=CustomResponse(replace_result=[response]))
    expected["name"] = response["displayName"]
    assert api.get_data(["FI"]) == [StandardStockInfo(**expected)]


def test_get_data_codes():
    num = randint(1, 100)
    api = CYahooAPI(response=CustomResponse(status_code=404))
    assert api.get_data(["NMB"] * num) == [None] * num

    api = CYahooAPI(response=CustomResponse(status_code=407))
    assert api.get_data(["NMB"] * num) == [None] * num
    assert api.working == False


def test_get_data_empty():
    num = randint(1, 100)
    api = CYahooAPI(response=CustomResponse(replace_result=""))
    assert api.get_data([]) == []
    assert api.get_data(["NMB"] * num) == [None] * num

    data = CustomResponse(replace_result="").json()
    data["quoteResponse"]["result"] = None
    api = CYahooAPI(response=CustomResponse(replace_json=data))
    assert api.get_data([]) == []
    assert api.get_data(["NMB"] * num) == [None] * num

    # api error
    api = CYahooAPI(response=CustomResponse(error="some error"))
    assert api.get_data([]) == []
    assert api.get_data(["NMB"] * num) == [None] * num

    api = CYahooAPI(response=CustomResponse(replace_result="gibber"))
    with pytest.raises(AttributeError) as e:
        api.get_data(["NMB"]) == []


def test_get_data_exception():
    api = CYahooAPI(response=CustomResponse(replace_json=[]))
    with pytest.raises(TypeError) as e:
        api.get_data([])

    api = CYahooAPI(response=CustomResponse(replace_json={}))
    with pytest.raises(KeyError) as e:
        api.get_data([])
