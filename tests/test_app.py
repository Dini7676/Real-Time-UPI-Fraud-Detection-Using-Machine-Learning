import pytest
from urllib.parse import urlparse

@pytest.fixture
def app_module():
    import UPIGUARD.app as app_module
    app_module.app.config["TESTING"] = True
    return app_module

@pytest.fixture
def client(app_module):
    return app_module.app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app_module):
    session = app_module._db_session()
    try:
        session.query(app_module.Transaction).delete()
        session.query(app_module.Merchant).delete()
        session.query(app_module.User).delete()
        session.commit()
    finally:
        session.close()
    yield
    session = app_module._db_session()
    try:
        session.query(app_module.Transaction).delete()
        session.query(app_module.Merchant).delete()
        session.query(app_module.User).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def create_user(app_module):
    def _create(**overrides):
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "mobile": "9957000001",
            "dob": "1990-01-01",
            "age": 30,
            "address": "123 Street",
            "state": "Karnataka",
            "zip": "560001",
            "role": "user",
            "upi": "user@upi",
        }
        payload.update(overrides)
        session = app_module._db_session()
        try:
            user = app_module.User(**payload)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        finally:
            session.close()

    return _create


def test_home_status_200(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_login_post_redirect(client, monkeypatch, app_module, create_user):
    # Avoid SMTP side effects
    monkeypatch.setattr(app_module, "send_otp_email", lambda to, otp: False)
    user = create_user()
    data = {"mobile": user.mobile, "role": "user"}
    resp = client.post("/login", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/verify_otp"


def test_verify_otp_success_user(client, create_user):
    user = create_user()
    with client.session_transaction() as sess:
        sess["pending_role"] = "user"
        sess["pending_user_id"] = user.id
        sess["pending_email"] = user.email
    resp = client.post("/verify_otp", data={"otp": "123456"}, follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/user/dashboard"

    with client.session_transaction() as sess:
        assert sess.get("role") == "user"
        assert sess.get("user_id") == user.id


def test_generate_qr_png(client, create_user, app_module):
    user = create_user()
    session = app_module._db_session()
    try:
        merchant = app_module.Merchant(user_id=user.id, category="Retail", qr_code="merchant@upi")
        session.add(merchant)
        session.commit()
        session.refresh(merchant)
        merchant_id = merchant.merchant_id
    finally:
        session.close()

    with client.session_transaction() as sess:
        sess["role"] = "user"
        sess["user_id"] = user.id

    resp = client.get(f"/generate_qr?merchant_id={merchant_id}")
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"


def test_merchant_transactions_view(client, create_user, app_module):
    user = create_user()
    session = app_module._db_session()
    try:
        merchant = app_module.Merchant(user_id=user.id, category="Retail", qr_code="merchant@upi")
        tx = app_module.Transaction(sender="9876543210", receiver="merchant@upi", amount=250.0, prediction="safe")
        session.add_all([merchant, tx])
        session.commit()
    finally:
        session.close()

    with client.session_transaction() as sess:
        sess["role"] = "user"
        sess["user_id"] = user.id

    resp = client.get("/merchant/transactions")
    assert resp.status_code == 200
    assert b"250.00" in resp.data


def test_user_transactions_view(client, create_user, app_module):
    user = create_user()
    session = app_module._db_session()
    try:
        tx = app_module.Transaction(sender=user.mobile, receiver="merchant@upi", amount=150.0, prediction="fraud")
        session.add(tx)
        session.commit()
    finally:
        session.close()

    with client.session_transaction() as sess:
        sess["role"] = "user"
        sess["user_id"] = user.id

    resp = client.get("/user/transactions")
    assert resp.status_code == 200
    assert b"150.00" in resp.data


def test_admin_transactions_view(client, create_user, app_module):
    user = create_user()
    session = app_module._db_session()
    try:
        tx = app_module.Transaction(sender=user.mobile, receiver="merchant@upi", amount=90.0, prediction="safe")
        session.add(tx)
        session.commit()
    finally:
        session.close()

    with client.session_transaction() as sess:
        sess["role"] = "admin"

    resp = client.get("/admin/transactions")
    assert resp.status_code == 200
    assert b"90.00" in resp.data


def test_detect_fraud_redirect(client, monkeypatch, app_module, create_user):
    user = create_user()
    monkeypatch.setattr(app_module, "get_model", lambda: None)
    monkeypatch.setattr(app_module, "get_preprocessor", lambda: None)

    with client.session_transaction() as sess:
        sess["role"] = "user"
        sess["user_id"] = user.id

    resp = client.get(
        "/detect_fraud?sender=9876543210&receiver=merchant@upi&amount=100&location=Bangalore",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/result"


def test_admin_create_account_redirect(client, app_module):
    with client.session_transaction() as sess:
        sess["role"] = "admin"

    form = {
        "name": "Alice",
        "email": "alice@example.com",
        "mobile": "9999999999",
        "dob": "1990-01-01",
        "age": "35",
        "address": "123 St",
        "state": "KA",
        "zip": "560001",
        "role": "user",
        "upi": "alice@upi",
    }
    resp = client.post("/admin/create_account", data=form, follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/admin/dashboard"

    session = app_module._db_session()
    try:
        created = session.query(app_module.User).filter_by(email="alice@example.com").first()
        assert created is not None
    finally:
        session.close()


def test_admin_create_account_rejects_invalid_mobile(client, app_module):
    with client.session_transaction() as sess:
        sess["role"] = "admin"

    form = {
        "name": "Invalid Mobile",
        "email": "bad@example.com",
        "mobile": "99-99-99",
        "dob": "1990-01-01",
        "age": "35",
        "address": "123 St",
        "state": "KA",
        "zip": "560001",
        "role": "user",
        "upi": "bad@upi",
    }
    resp = client.post("/admin/create_account", data=form, follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/admin/create_account"

    session = app_module._db_session()
    try:
        created = session.query(app_module.User).filter_by(email="bad@example.com").first()
        assert created is None
    finally:
        session.close()


def test_login_normalizes_existing_mobile(client, monkeypatch, app_module):
    monkeypatch.setattr(app_module, "send_otp_email", lambda to, otp: False)

    session = app_module._db_session()
    try:
        legacy_mobile = "+91 99570 00005"
        user = app_module.User(
            name="Legacy",
            email="legacy@example.com",
            mobile=legacy_mobile,
            dob="1990-01-01",
            age=30,
            address="123",
            state="KA",
            zip="560001",
            role="user",
            upi="legacy@upi",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id
    finally:
        session.close()

    resp = client.post("/login", data={"mobile": "9957000005", "role": "user"}, follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/verify_otp"

    session = app_module._db_session()
    try:
        refreshed = session.get(app_module.User, user_id)
        assert refreshed.mobile == "9957000005"
    finally:
        session.close()
