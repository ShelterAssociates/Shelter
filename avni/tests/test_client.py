"""AvniClient: token caching, retries, paging and counting against a fake transport."""

import base64
import json
import time

from django.test import SimpleTestCase

from avni import client as client_module
from avni.client import AvniClient, AvniError


def fake_jwt(expires_in_seconds):
    payload = json.dumps({"exp": int(time.time()) + expires_in_seconds}).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return "header.{}.signature".format(encoded)


class FakeResponse(object):
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self.body = body if body is not None else {}
        self.text = json.dumps(self.body)

    def json(self):
        return self.body


class FakeTransport(object):
    """Stands in for requests.request; answers from a queue and records calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        if not self.responses:
            return FakeResponse(200, {})
        return self.responses.pop(0)


class FakeTokenSource(object):
    def __init__(self, tokens):
        self.tokens = list(tokens)
        self.fetches = 0

    def fetch(self):
        self.fetches += 1
        return self.tokens.pop(0)


def make_client(responses, tokens=None, **kwargs):
    transport = FakeTransport(responses)
    tokens = FakeTokenSource(tokens or [fake_jwt(3600)])
    avni = AvniClient(
        base_url="https://avni.test/",
        token_source=tokens,
        transport=transport,
        sleep=lambda seconds: None,
        **kwargs
    )
    return avni, transport, tokens


class TokenTests(SimpleTestCase):
    def test_token_is_fetched_once_and_reused(self):
        avni, transport, tokens = make_client([FakeResponse(), FakeResponse()])
        avni.get("api/subject/1")
        avni.get("api/subject/2")
        self.assertEqual(tokens.fetches, 1)
        for call in transport.calls:
            self.assertEqual(call["kwargs"]["headers"]["auth-token"], avni.token())

    def test_token_is_refreshed_when_close_to_expiry(self):
        avni, transport, tokens = make_client(
            [FakeResponse(), FakeResponse()],
            tokens=[fake_jwt(10), fake_jwt(3600)],
        )
        avni.get("api/subject/1")
        avni.get("api/subject/2")
        self.assertEqual(tokens.fetches, 2)

    def test_401_refreshes_token_and_retries_once(self):
        avni, transport, tokens = make_client(
            [FakeResponse(401), FakeResponse(200, {"ID": "x"})],
            tokens=[fake_jwt(3600), fake_jwt(3600)],
        )
        response = avni.get("api/subject/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(tokens.fetches, 2)
        self.assertEqual(len(transport.calls), 2)


class RequestTests(SimpleTestCase):
    def test_get_json_returns_body(self):
        avni, transport, tokens = make_client([FakeResponse(200, {"ID": "abc"})])
        self.assertEqual(avni.get_json("api/subject/abc"), {"ID": "abc"})
        self.assertEqual(transport.calls[0]["url"], "https://avni.test/api/subject/abc")

    def test_get_json_raises_on_error_status(self):
        avni, transport, tokens = make_client([FakeResponse(404, {"message": "nope"})])
        with self.assertRaises(AvniError) as raised:
            avni.get_json("api/subject/missing")
        self.assertEqual(raised.exception.status_code, 404)

    def test_put_and_patch_send_json_body(self):
        avni, transport, tokens = make_client([FakeResponse(), FakeResponse()])
        avni.put("api/subject/1", {"observations": {"A": 1}})
        avni.patch("api/encounter/2", {"Voided": True})
        self.assertEqual(transport.calls[0]["method"], "PUT")
        self.assertEqual(json.loads(transport.calls[0]["kwargs"]["data"]), {"observations": {"A": 1}})
        self.assertEqual(transport.calls[1]["method"], "PATCH")
        self.assertEqual(transport.calls[1]["kwargs"]["headers"]["Content-Type"], "application/json")

    def test_every_request_has_a_timeout(self):
        avni, transport, tokens = make_client([FakeResponse()], timeout=42)
        avni.get("api/subject/1")
        self.assertEqual(transport.calls[0]["kwargs"]["timeout"], 42)


class PagingTests(SimpleTestCase):
    def page(self, content, total_pages, page_size=20):
        return FakeResponse(200, {"content": content, "totalPages": total_pages, "pageSize": page_size})

    def test_iter_pages_walks_every_page(self):
        avni, transport, tokens = make_client([
            self.page(["a", "b"], 3),
            self.page(["c"], 3),
            self.page(["d"], 3),
        ])
        pages = list(avni.iter_pages("api/subjects?subjectType=Household"))
        self.assertEqual(pages, [["a", "b"], ["c"], ["d"]])
        self.assertTrue(transport.calls[1]["url"].endswith("&page=1"))
        self.assertTrue(transport.calls[2]["url"].endswith("&page=2"))

    def test_iter_pages_uses_question_mark_when_path_has_no_query(self):
        avni, transport, tokens = make_client([self.page(["a"], 2), self.page(["b"], 2)])
        list(avni.iter_pages("api/subjects"))
        self.assertTrue(transport.calls[1]["url"].endswith("api/subjects?page=1"))

    def test_count_uses_last_page_length_not_total_elements(self):
        avni, transport, tokens = make_client([
            self.page(["x"] * 20, 3, page_size=20),
            self.page(["x"] * 7, 3, page_size=20),
        ])
        summary = avni.count("api/subjects?subjectType=Household")
        self.assertEqual(summary, {"total": 47, "pages": 3, "page_size": 20})
        self.assertTrue(transport.calls[1]["url"].endswith("&page=2"))

    def test_count_single_page(self):
        avni, transport, tokens = make_client([self.page(["x"] * 5, 1, page_size=20)])
        self.assertEqual(avni.count("api/subjects")["total"], 5)
        self.assertEqual(len(transport.calls), 1)

    def test_count_empty(self):
        avni, transport, tokens = make_client([self.page([], 0, page_size=20)])
        self.assertEqual(avni.count("api/subjects")["total"], 0)


class ThrottleTests(SimpleTestCase):
    def test_pauses_after_every_batch(self):
        pauses = []
        transport = FakeTransport([FakeResponse()] * 6)
        avni = AvniClient(
            base_url="https://avni.test/",
            token_source=FakeTokenSource([fake_jwt(3600)]),
            transport=transport,
            sleep=pauses.append,
            batch_size=3,
            batch_pause_seconds=5,
        )
        for i in range(6):
            avni.get("api/subject/{}".format(i))
        self.assertEqual(pauses, [5, 5])


class SignedMediaTests(SimpleTestCase):
    def test_signed_media_url_returns_body_text(self):
        avni, transport, tokens = make_client([FakeResponse(200, "https://s3/signed")])
        transport.responses = [FakeResponse(200, "https://s3/signed")]
        signed = avni.signed_media_url("https://s3/raw.jpg")
        self.assertEqual(signed, "https://s3/signed")
        self.assertIn("media/signedUrl?url=https%3A%2F%2Fs3%2Fraw.jpg", transport.calls[0]["url"])


class ProcessWideClientTests(SimpleTestCase):
    def test_client_returns_same_instance(self):
        client_module.reset_client()
        self.assertIs(client_module.client(), client_module.client())
        client_module.reset_client()
