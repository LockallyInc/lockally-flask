# Lockally for Flask

Official [Lockally](https://lockally.com) extension for Flask. Send transactional
email from any view with a small, idiomatic `Lockally(app)` extension.

## Install

```bash
pip install lockally-flask
```

## Configure

```python
from flask import Flask
from lockally_flask import Lockally

app = Flask(__name__)
app.config["LOCKALLY_API_KEY"] = "lk_live_xxx"      # lk_test_xxx runs in sandbox
# app.config["LOCKALLY_BASE_URL"] = "https://api.lockally.com"   # optional override
lockally = Lockally(app)
```

The application-factory pattern is supported too:

```python
lockally = Lockally()

def create_app():
    app = Flask(__name__)
    app.config["LOCKALLY_API_KEY"] = "lk_live_xxx"
    lockally.init_app(app)
    return app
```

## Send

```python
from lockally_flask import send_email

@app.post("/signup")
def signup():
    send_email(
        from_="alerts@yourdomain.com",
        to="user@example.com",
        subject="Welcome",
        text="Thanks for signing up.",
        html="<b>Thanks for signing up.</b>",
        reply_to="support@yourdomain.com",
        attachments=[("welcome.pdf", pdf_bytes, "application/pdf")],
    )
    return "", 202
```

`send_email` uses the client registered on the current app, so blueprints can call it
without holding a reference. `to`/`cc`/`bcc`/`reply_to` accept a single address or a
list; `attachments` is a list of `(filename, content, content_type)` (content is bytes
or str).

### Mapping notes

- **Reply-To** is sent as a header (Lockally has no `reply_to` field).
- **Attachments** are base64-encoded as `{filename, content_type, content_base64}`.
- One `Idempotency-Key` is generated per send (24 h dedupe window).

## License

MIT © Lockally
