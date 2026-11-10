"""Unit tests for extract, with mocked HTTP. No network."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
import requests

from pipeline.extract import fetch_api, fetch_csv, make_session, save_raw


def fake_response(rows):
    resp = MagicMock()
    resp.json.return_value = {"results": rows}
    return resp


def test_pagination_stops_on_short_page():
    session = MagicMock()
    session.get.side_effect = [fake_response([{"a": 1}] * 2), fake_response([{"a": 1}])]

    df = fetch_api("https://example.test", page_size=2, session=session)

    assert len(df) == 3
    assert session.get.call_count == 2


def test_offsets_advance_by_page_size():
    session = MagicMock()
    session.get.side_effect = [
        fake_response([{"a": 1}] * 2),
        fake_response([{"a": 2}] * 2),
        fake_response([]),  # an exact multiple of the page size ends on an empty page
    ]

    df = fetch_api("https://example.test", page_size=2, session=session)

    params = [call.kwargs["params"] for call in session.get.call_args_list]
    assert [p["offset"] for p in params] == [0, 2, 4]
    assert all(p["limit"] == 2 for p in params)
    assert len(df) == 4


def test_every_request_has_a_timeout():
    session = MagicMock()
    session.get.return_value = fake_response([])

    fetch_api("https://example.test", session=session)

    assert session.get.call_args.kwargs["timeout"] > 0


def test_http_error_is_raised_not_swallowed():
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")
    session = MagicMock()
    session.get.return_value = resp

    with pytest.raises(requests.HTTPError):
        fetch_api("https://example.test", session=session)


def test_session_retries_throttling_and_server_errors():
    retry = make_session().get_adapter("https://data.medicaid.gov").max_retries

    assert retry.total == 3
    assert retry.backoff_factor == 1
    assert {429, 500, 502, 503, 504} <= set(retry.status_forcelist)


def test_fetch_csv_reads_a_local_file(fixture_path):
    df = fetch_csv(str(fixture_path))

    assert df.shape == (20, 44)
    assert "State Abbreviation" in df.columns


def test_fetch_csv_from_a_url_goes_through_the_session(fixture_path):
    resp = MagicMock()
    resp.content = fixture_path.read_bytes()
    session = MagicMock()
    session.get.return_value = resp

    df = fetch_csv("https://example.test/enrollment.csv", session=session)

    assert len(df) == 20
    resp.raise_for_status.assert_called_once()
    assert session.get.call_args.kwargs["timeout"] > 0


def test_save_raw_writes_an_untouched_copy(tmp_path, raw_df):
    path = save_raw(raw_df, tmp_path / "snapshots")

    assert path.parent == tmp_path / "snapshots"
    saved = pd.read_csv(path)
    assert saved.shape == raw_df.shape
    assert list(saved.columns) == list(raw_df.columns)
