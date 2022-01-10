#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from source_chartmogul.source import Customers, Activities, ChartmogulStream


@pytest.fixture
def patch_base_class(mocker):
    # Mock abstract methods to enable instantiating abstract class
    mocker.patch.object(Customers, "__abstractmethods__", set())
    mocker.patch.object(Activities, "__abstractmethods__", set())


# Customer stream tests

def test_request_params():
    stream = Customers()
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_params = {"page": 1}
    assert stream.request_params(**inputs) == expected_params

    next_page_token = {"page": 3}
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": next_page_token}
    expected_params = {"page": 3}
    assert stream.request_params(**inputs) == expected_params


def test_next_page_token():
    stream = Customers()
    response = MagicMock()

    # no more results
    response.json.return_value =  {"has_more": False} 
    inputs = {"response": response}
    assert stream.next_page_token(**inputs) == None

    # there is more results
    response.json.return_value =  {"has_more": True, "current_page": 42} 
    inputs = {"response": response}
    assert stream.next_page_token(**inputs) == {"page": 43}


def test_parse_response():
    stream = Customers()
    response = MagicMock()
    response.json.return_value =  {"entries": [{"one": 1}, {"two": 2}]} 
    inputs = {"response": response}
    expected_parsed_object = {"one": 1}
    assert next(stream.parse_response(**inputs)) == expected_parsed_object

# Activites stream tests

def test_request_params_activities():
    # no start_date set
    stream = Activities(start_date=None)
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    assert stream.request_params(**inputs) == {}
    
    # start_date is set
    stream.start_date = "2010-01-01"
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    assert stream.request_params(**inputs) == {"start-date": stream.start_date}

    # start-after is available
    next_page_token = {"start-after": "a-b-c"}
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": next_page_token}
    expected_params = next_page_token
    assert stream.request_params(**inputs) == expected_params


def test_next_page_token_activities():
    stream = Activities(start_date=None)
    response = MagicMock()

    # no more results
    response.json.return_value = {"has_more": False} 
    inputs = {"response": response}
    assert stream.next_page_token(**inputs) == None

    # there is more results
    response.json.return_value =  {"has_more": True, "entries": [{"uuid": "unique-uuid"}]} 
    inputs = {"response": response}
    assert stream.next_page_token(**inputs) == {"start-after": "unique-uuid"}


# Default tests

@pytest.mark.parametrize(
    ("http_status", "should_retry"),
    [
        (HTTPStatus.OK, False),
        (HTTPStatus.BAD_REQUEST, False),
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.INTERNAL_SERVER_ERROR, True),
    ],
)

def test_should_retry(http_status, should_retry):
    response_mock = MagicMock()
    response_mock.status_code = http_status
    stream = Customers()
    assert stream.should_retry(response_mock) == should_retry


def test_backoff_time():
    response_mock = MagicMock()
    stream = Customers()
    expected_backoff_time = None
    assert stream.backoff_time(response_mock) == expected_backoff_time
