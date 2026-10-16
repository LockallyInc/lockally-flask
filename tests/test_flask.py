import base64
import unittest

from flask import Flask

from lockally_flask import Lockally, send_email
from lockally_flask.client import LockallyClient


class FakeSendApi:
    def __init__(self):
        self.calls = []

    def v1_send_post(self, idempotency_key, request):
        self.calls.append((idempotency_key, request))
        return {"id": "m_1", "status": "queued"}


class LockallyClientMappingTest(unittest.TestCase):
    def test_build_payload_maps_fields(self):
        payload = LockallyClient.build_payload(
            from_="Acme Alerts <alerts@acme.com>",
            to=["user@example.com", "Second <two@example.com>"],
            cc="cc@example.com",
            reply_to="reply@acme.com",
            subject="Your code",
            text="code 123",
            html="<b>code 123</b>",
            headers={"X-Campaign": "welcome"},
            attachments=[("invoice.pdf", b"BYTES", "application/pdf")],
        )
        self.assertEqual(payload["from"], "alerts@acme.com")  # display name stripped
        self.assertEqual(payload["to"], ["user@example.com", "two@example.com"])
        self.assertEqual(payload["cc"], ["cc@example.com"])
        self.assertEqual(payload["subject"], "Your code")
        self.assertEqual(payload["text"], "code 123")
        self.assertEqual(payload["html"], "<b>code 123</b>")
        self.assertEqual(payload["headers"]["Reply-To"], "reply@acme.com")
        self.assertEqual(payload["headers"]["X-Campaign"], "welcome")
        att = payload["attachments"][0]
        self.assertEqual(att["filename"], "invoice.pdf")
        self.assertEqual(att["content_type"], "application/pdf")
        self.assertEqual(att["content_base64"], base64.b64encode(b"BYTES").decode())

    def test_send_email_calls_api_with_idempotency_key(self):
        fake = FakeSendApi()
        client = LockallyClient(send_api=fake)
        client.send_email(from_="a@acme.com", to="b@example.com", subject="hi", text="yo")

        self.assertEqual(len(fake.calls), 1)
        key, request = fake.calls[0]
        self.assertTrue(key.startswith("lk-"))
        self.assertEqual(request.to_dict()["from"], "a@acme.com")
        self.assertEqual(request.to_dict()["to"], ["b@example.com"])


class FlaskExtensionTest(unittest.TestCase):
    def _app(self, fake):
        app = Flask(__name__)
        app.config["LOCKALLY_API_KEY"] = "lk_test_abc"
        Lockally(app)
        app.extensions["lockally"]._send_api = fake  # inject mock
        return app

    def test_extension_registers_client(self):
        app = self._app(FakeSendApi())
        self.assertIsInstance(app.extensions["lockally"], LockallyClient)

    def test_module_send_email_uses_current_app(self):
        fake = FakeSendApi()
        app = self._app(fake)
        with app.app_context():
            send_email(from_="a@acme.com", to="b@example.com", subject="hi", text="yo")
        self.assertEqual(len(fake.calls), 1)

    def test_send_email_outside_app_context_raises(self):
        with self.assertRaises(RuntimeError):
            send_email(from_="a@acme.com", to="b@example.com")


if __name__ == "__main__":
    unittest.main()
