import os
import sys
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, abort
# Workaround: avoid potential hang importing SQLAlchemy cyextensions on some Windows setups
os.environ.setdefault("SQLALCHEMY_DISABLE_CYEXTENSIONS", "1")
# Ensure local 'src' package is importable both when run as script and when imported as a module
_here = os.path.dirname(__file__)
if _here not in sys.path:
    sys.path.insert(0, _here)

from src.db import init_db, SessionLocal, User, Merchant, Transaction, RiskStat
from sqlalchemy import func
import re
import qrcode
from io import BytesIO
import smtplib
from email.mime.text import MIMEText

# Load environment variables from .env located next to this file
try:
    load_dotenv(os.path.join(_here, ".env"))
except Exception:
    # Fallback to default .env search if explicit path fails
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "upiguard-secret")

# Suppress noisy access logs for static files (e.g., /static/js/script.js 304)
class _NoStaticFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/static/" not in msg

_werk = logging.getLogger("werkzeug")
if os.getenv("UPIGUARD_SILENCE_STATIC", "1") == "1":
    _werk.addFilter(_NoStaticFilter())

# Load ML preprocessor and model lazily
PREPROCESSOR_PATH = os.path.join(os.path.dirname(__file__), "dataset", "preprocessor.joblib")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "model1.h5")
_preprocessor = None
_model = None


def _db_session():
    return SessionLocal()


def _normalize_mobile(value: Optional[str]) -> str:
    if not value:
        return ""
    digits_only = "".join(ch for ch in value if ch.isdigit())
    if len(digits_only) > 10:
        return digits_only[-10:]
    return digits_only


def get_current_user() -> Optional[User]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    s = _db_session()
    try:
        user = s.get(User, user_id)
        return user
    finally:
        s.close()


def user_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in as a user.")
            return redirect(url_for("login"))
        return view_func(user, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def get_preprocessor():
    global _preprocessor
    if _preprocessor is None and os.path.exists(PREPROCESSOR_PATH):
        try:
            import joblib  # lazy import; avoid importing numpy at startup
            _preprocessor = joblib.load(PREPROCESSOR_PATH)
        except Exception:
            _preprocessor = None
    return _preprocessor


def get_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        try:
            import tensorflow as tf  # lazy import; optional dependency
        except Exception:
            return None
        _model = tf.keras.models.load_model(MODEL_PATH)
    return _model


# Initialize DB at startup (Flask 3 removed before_first_request)
init_db()


# Routes
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        otp = "123456"

        if role == "user":
            mobile = _normalize_mobile(request.form.get("mobile"))
            if len(mobile) != 10:
                flash("Enter a valid 10-digit mobile number to continue.")
                return redirect(url_for("login"))

            resolved_user = None
            resolved_email = None
            s = _db_session()
            try:
                user = s.query(User).filter(User.mobile == mobile).first()
                if not user:
                    candidates = s.query(User).filter(User.mobile.isnot(None)).all()
                    for candidate in candidates:
                        if _normalize_mobile(candidate.mobile) == mobile:
                            user = candidate
                            break
                    if user and user.mobile != mobile:
                        user.mobile = mobile
                        s.commit()
                if user:
                    resolved_user = user.id
                    resolved_email = user.email
            finally:
                s.close()

            if not resolved_user:
                flash("Mobile number not found. Ask an admin to create your account.")
                return redirect(url_for("login"))

            session.clear()
            session["pending_role"] = "user"
            session["pending_user_id"] = resolved_user
            session["pending_email"] = resolved_email or f"{mobile}@example.com"

            if send_otp_email(session["pending_email"], otp):
                flash("OTP sent to your email address.")
            else:
                flash("SMTP not configured. Use OTP 123456 to continue.")
            return redirect(url_for("verify_otp"))

        if role == "admin":
            username = (request.form.get("username") or "").strip()
            password = (request.form.get("password") or "").strip()
            admin_user = os.getenv("ADMIN_USERNAME", "admin")
            admin_pass = os.getenv("ADMIN_PASSWORD", "admin")

            if username != admin_user or password != admin_pass:
                flash("Invalid admin credentials.")
                return redirect(url_for("login"))

            session.clear()
            session["role"] = "admin"
            session["admin_username"] = username
            flash("Logged in as admin.")
            return redirect(url_for("admin_dashboard"))

        flash("Choose a valid role to log in.")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    pending_role = session.get("pending_role")
    if request.method == "POST":
        entered = request.form.get("otp")
        if entered == "123456":
            if pending_role == "user":
                user_id = session.pop("pending_user_id", None)
                session.pop("pending_email", None)
                session.pop("pending_role", None)
                if not user_id:
                    flash("Session expired. Please log in again.")
                    return redirect(url_for("login"))

                session.clear()
                session["role"] = "user"
                session["user_id"] = user_id
                flash("OTP verified. Welcome back!")
                return redirect(url_for("user_dashboard"))

            flash("Session expired. Please log in again.")
            return redirect(url_for("login"))
        flash("Invalid OTP")
    return render_template("verify_otp.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/admin/create_account", methods=["GET", "POST"])
@admin_required
def admin_create_account():
    if request.method == "POST":
        mobile = _normalize_mobile(request.form.get("mobile"))
        if len(mobile) != 10:
            flash("Enter a valid 10-digit mobile number to continue.")
            return redirect(url_for("admin_create_account"))

        s = _db_session()
        try:
            existing = s.query(User).filter(User.mobile == mobile).first()
            if existing:
                flash("This mobile number is already registered.")
                return redirect(url_for("admin_create_account"))

            user = User(
                name=request.form.get("name"),
                email=request.form.get("email"),
                mobile=mobile,
                dob=request.form.get("dob"),
                age=int(request.form.get("age") or 0),
                address=request.form.get("address"),
                state=request.form.get("state"),
                zip=request.form.get("zip"),
                role=request.form.get("role"),
                upi=request.form.get("upi"),
            )
            s.add(user)
            s.commit()
        finally:
            s.close()
        flash("Account created")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_create_account.html")


@app.route("/admin/users")
@admin_required
def admin_users():
    s = _db_session()
    users = s.query(User).order_by(User.id.asc()).all()
    s.close()
    return render_template("admin_users.html", users=users)


@app.route("/admin/merchants")
@admin_required
def admin_merchants():
    s = _db_session()
    merchants = s.query(Merchant).all()
    s.close()
    return render_template("admin_merchants.html", merchants=merchants)


@app.route("/admin/transactions")
@admin_required
def admin_transactions():
    s = _db_session()
    txs = s.query(Transaction).order_by(Transaction.timestamp.desc()).all()
    s.close()
    return render_template("admin_transactions.html", transactions=txs)


@app.route("/merchant/setup", methods=["GET", "POST"])
@user_required
def merchant_setup(current_user):
    if request.method == "POST":
        upi_value = (request.form.get("upi") or "").strip()
        category = (request.form.get("category") or "").strip()
        # Validate user mobile: must be exactly 10 digits
        normalized_mobile = _normalize_mobile(current_user.mobile)
        if len(normalized_mobile) != 10:
            flash("Add a valid 10-digit mobile number to your profile before merchant setup.")
            return redirect(url_for("user_profile"))

        if not upi_value or not category:
            flash("Provide both UPI ID and category to continue.")
            return redirect(url_for("merchant_setup"))

        # UPI format: exactly 10 digits followed by '@' and provider (letters/numbers/dots/dashes)
        upi_pattern = re.compile(r"^[0-9]{10}@[A-Za-z0-9._-]+$")
        if not upi_pattern.match(upi_value):
            flash("UPI must be exactly 10 digits followed by '@provider' (e.g., 9957000001@securepay). Only digits allowed before '@'.")
            return redirect(url_for("merchant_setup"))

        s = _db_session()
        try:
            # Ensure UPI uniqueness across merchants
            existing = s.query(Merchant).filter(Merchant.qr_code == upi_value).first()
            if existing:
                flash("This UPI is already registered. Please choose a different unique UPI.")
                return redirect(url_for("merchant_setup"))
            merchant = Merchant(
                user_id=current_user.id,
                category=category,
                qr_code=upi_value
            )
            s.add(merchant)
            s.commit()
        finally:
            s.close()

        flash("Merchant setup saved. Access your merchant dashboard for full details.")
        return redirect(url_for("merchant_dashboard"))
    return render_template("merchant_setup.html", user=current_user)


@app.route("/merchant/dashboard")
@user_required
def merchant_dashboard(current_user):
    s = _db_session()
    try:
        merchant = s.query(Merchant).filter(Merchant.user_id == current_user.id).first()
        if merchant:
            _ = merchant.owner
    finally:
        s.close()
    return render_template("merchant_dashboard.html", user=current_user, merchant=merchant)


@app.route("/merchant/profile")
@user_required
def merchant_profile(current_user):
    s = _db_session()
    try:
        merchant = s.query(Merchant).filter(Merchant.user_id == current_user.id).first()
        if merchant:
            _ = merchant.owner
            created_at = getattr(merchant, "created_at", None)
            merchant.created_display = created_at.strftime("%Y-%m-%d") if created_at else None
    finally:
        s.close()
    if not merchant:
        flash("Complete your merchant setup first.")
        return redirect(url_for("merchant_setup"))
    return render_template("merchant_profile.html", user=current_user, merchant=merchant)


@app.route("/generate_qr")
@user_required
def generate_qr(current_user):
    merchant_id = request.args.get("merchant_id")
    try:
        merchant_id_int = int(merchant_id)
    except (TypeError, ValueError):
        abort(404)

    s = _db_session()
    try:
        merchant = s.query(Merchant).filter(Merchant.merchant_id == merchant_id_int).first()
        if merchant:
            owner_name = merchant.owner.name if merchant.owner else None
            merchant_user_id = merchant.user_id
            upi_value = merchant.qr_code
        else:
            owner_name = None
            merchant_user_id = None
            upi_value = None
    finally:
        s.close()

    if not merchant or merchant_user_id != current_user.id:
        abort(404)

    recipient = owner_name or f"Merchant{merchant_id_int}"
    upi_target = upi_value or "merchant@upi"
    payload = f"upi://pay?pa={upi_target}&pn={recipient}&am=0&cu=INR"
    img = qrcode.make(payload)
    buf = BytesIO()
    try:
        img.save(buf, format='PNG')
    except TypeError:
        # Pure Python backend (pypng) may not accept 'format'
        img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route("/merchant/transactions")
@user_required
def merchant_transactions(current_user):
    s = _db_session()
    try:
        merchant = s.query(Merchant).filter(Merchant.user_id == current_user.id).first()
        if not merchant:
            flash("Complete your merchant setup first.")
            return redirect(url_for("merchant_setup"))

        transactions = (
            s.query(Transaction)
            .filter(Transaction.receiver == merchant.qr_code)
            .order_by(Transaction.timestamp.desc())
            .all()
        )
    finally:
        s.close()

    return render_template(
        "merchant_transactions.html",
        user=current_user,
        merchant=merchant,
        transactions=transactions,
    )


@app.route("/user/dashboard")
@user_required
def user_dashboard(current_user):
    return render_template("user_dashboard.html", user=current_user)

@app.route("/user/transactions")
@user_required
def user_transactions(current_user):
    s = _db_session()
    try:
        sender_value = current_user.mobile or ""
        transactions = (
            s.query(Transaction)
            .filter(Transaction.sender == sender_value)
            .order_by(Transaction.timestamp.desc())
            .all()
        )
    finally:
        s.close()
    return render_template("user_transactions.html", user=current_user, transactions=transactions)

@app.route("/user/profile")
@user_required
def user_profile(current_user):
    return render_template("user_profile.html", user=current_user)


@app.route("/make_payment", methods=["GET", "POST"])
@user_required
def make_payment(current_user):
    s = _db_session()
    try:
        merchants = s.query(Merchant).order_by(Merchant.merchant_id.asc()).all()
        for m in merchants:
            _ = m.owner
    finally:
        s.close()

    if request.method == "POST":
        merchant_id_raw = request.form.get("merchant_id")
        custom_receiver = (request.form.get("receiver") or "").strip()
        location = (request.form.get("location") or current_user.state or "Bangalore").strip() or "Bangalore"
        amount_raw = (request.form.get("amount") or "0").strip()

        try:
            amount = float(amount_raw)
        except ValueError:
            flash("Enter a valid amount.")
            return render_template("make_payment.html", user=current_user, merchants=merchants)

        if amount <= 0:
            flash("Amount must be greater than zero.")
            return render_template("make_payment.html", user=current_user, merchants=merchants)

        merchant_id = None
        resolved_receiver = None
        if merchant_id_raw:
            try:
                merchant_id = int(merchant_id_raw)
            except ValueError:
                merchant_id = None
            if merchant_id:
                s_lookup = _db_session()
                try:
                    merchant_obj = s_lookup.get(Merchant, merchant_id)
                finally:
                    s_lookup.close()
                if merchant_obj and merchant_obj.qr_code:
                    resolved_receiver = merchant_obj.qr_code
        if not resolved_receiver:
            resolved_receiver = custom_receiver

        if not resolved_receiver:
            flash("Select a merchant or enter a UPI ID to continue.")
            return render_template("make_payment.html", user=current_user, merchants=merchants)

        params = {
            "sender": current_user.mobile or "",
            "receiver": resolved_receiver,
            "amount": amount,
            "location": location,
        }
        if merchant_id:
            params["merchant_id"] = merchant_id

        return redirect(url_for("detect_fraud", **params))

    return render_template("make_payment.html", user=current_user, merchants=merchants)


@app.route("/scan_qr", methods=["GET", "POST"])
@user_required
def scan_qr(current_user):
    if request.method == "POST":
        f = request.files.get("qr")
        if f:
            # Simulate parsing: derive a payload from filename
            fname = f.filename or "qr.png"
            payload = f"upi://pay?pa=merchant@upi&pn={fname}&am=0&cu=INR"
            flash("QR parsed. Ready to pay.")
            return redirect(url_for("make_payment"))
        flash("No file uploaded")
    return render_template("scan_qr.html", user=current_user)


@app.route("/detect_fraud")
@user_required
def detect_fraud(current_user):
    sender_arg = request.args.get("sender", current_user.mobile or "9876543210")
    sender = _normalize_mobile(sender_arg)
    if len(sender) != 10:
        fallback = _normalize_mobile(current_user.mobile) or "9876543210"
        sender = fallback if len(fallback) == 10 else "9876543210"
    receiver = request.args.get("receiver", "merchant@upi")
    amount = float(request.args.get("amount", 0))
    location = request.args.get("location", "Bangalore")
    merchant_id = request.args.get("merchant_id", type=int)
    merchant = None

    # Build minimal feature row for prediction; demo values
    features = {
        "transaction_hour": 12,
        "transaction_date": 15,
        "transaction_month": 12,
        "transaction_year": 2025,
        "transaction_amount": amount,
        "transaction_category": "OnlineShopping",
        "state": "Karnataka",
        "zip_code": "560001",
        "location": location,
        "user_age": 30,
        "merchant_age": 24,
        "mobile_hash": abs(hash(sender)) % 1000000,
        "txn_hash": abs(hash("TXN12345678")) % 1000000,
    }

    # History-aware behavioral features computed from DB
    s_hist = _db_session()
    try:
        total_txn = s_hist.query(func.count(Transaction.id)).filter(Transaction.sender == sender).scalar() or 0
        fraud_txn = s_hist.query(func.count(Transaction.id)).filter(Transaction.sender == sender, Transaction.prediction == "fraud").scalar() or 0
        last5 = (
            s_hist.query(Transaction.amount, Transaction.timestamp)
            .filter(Transaction.sender == sender)
            .order_by(Transaction.timestamp.desc())
            .limit(5)
            .all()
        )
    finally:
        s_hist.close()

    recent_avg = 0.0
    last_time = None
    if last5:
        amounts = [row[0] or 0.0 for row in last5]
        recent_avg = sum(amounts) / max(1, len(amounts))
        last_time = last5[0][1]
    # Gap in hours from now to last txn (if any)
    try:
        now_dt = __import__("datetime").datetime.utcnow()
        gap_hours = float((now_dt - last_time).total_seconds() / 3600.0) if last_time else 24.0
    except Exception:
        gap_hours = 24.0

    fraud_rate = (fraud_txn / total_txn) if total_txn > 0 else 0.0

    features.update({
        "sender_total_txn": float(total_txn),
        "sender_fraud_txn": float(fraud_txn),
        "sender_fraud_rate": float(min(1.0, max(0.0, fraud_rate))),
        "sender_recent_amount_avg": float(recent_avg),
        "sender_recent_gap_hours": float(max(0.0, min(gap_hours, 24.0*30))),
    })

    pre = get_preprocessor()
    mdl = get_model()
    # Heuristic overrides from environment
    fraud_threshold = float(os.getenv("FRAUD_THRESHOLD", "0.4"))
    high_amount_limit = float(os.getenv("HIGH_AMOUNT_LIMIT", "50000"))
    blacklist_mobiles = {m.strip() for m in (os.getenv("FRAUD_MOBILE_LIST", "").split(",")) if m.strip()}
    blacklist_upis = {u.strip().lower() for u in (os.getenv("FRAUD_UPI_LIST", "").split(",")) if u.strip()}
    suspicious_substrings = [s.strip().lower() for s in os.getenv("SUSPICIOUS_UPI_SUBSTRINGS", "fraud,scam,hacker,testfail").split(",") if s.strip()]

    prediction_label = "safe"
    confidence = 0.0
    high_risk_flag = False

    # 1) Explicit business rules (can be disabled via env for evaluation)
    heuristics_enabled = os.getenv("FRAUD_HEURISTICS_ENABLED", "1") == "1"
    if heuristics_enabled:
        if amount > high_amount_limit:
            prediction_label = "fraud"
        if sender in blacklist_mobiles:
            prediction_label = "fraud"
        if any(sub in receiver.lower() for sub in suspicious_substrings) or receiver.lower() in blacklist_upis:
            prediction_label = "fraud"

    # 2) ML prediction if no heuristic flagged
    if prediction_label == "safe" and pre and mdl:
        try:
            import pandas as pd
            import numpy as np
        except Exception:
            pre = None
            mdl = None
        if pre and mdl:
            X = pd.DataFrame([features])
            Xt = pre.transform(X)
            # Add a trailing dimension without requiring numpy if unavailable
            try:
                Xt = np.expand_dims(Xt, axis=-1)
            except Exception:
                # Fallback: if Xt supports slicing, emulate expand_dims
                try:
                    Xt = Xt[..., None]
                except Exception:
                    pass
            proba = mdl.predict(Xt, verbose=0)[0][0]
            confidence = float(proba)
            prediction_label = "fraud" if proba >= fraud_threshold else "safe"

    # History reinforcement: if repeated frauds, mark high risk
    history_threshold = int(os.getenv("FRAUD_HISTORY_THRESHOLD", "3"))
    if fraud_txn >= history_threshold:
        prediction_label = "fraud"
        high_risk_flag = True
        confidence = max(confidence, 0.9)

    session = _db_session()
    try:
        if merchant_id:
            merchant = session.get(Merchant, merchant_id)
            if merchant and merchant.qr_code:
                receiver = merchant.qr_code

        tx = Transaction(sender=sender, receiver=receiver, amount=amount, prediction=prediction_label)
        session.add(tx)
        session.commit()

        # Update RiskStat for sender mobile
        try:
            stat = (
                session.query(RiskStat)
                .filter(RiskStat.identifier == sender, RiskStat.id_type == "mobile")
                .one_or_none()
            )
            if not stat:
                stat = RiskStat(identifier=sender, id_type="mobile", total_txn=0, fraud_txn=0)
                session.add(stat)
            stat.total_txn = int((stat.total_txn or 0) + 1)
            if prediction_label == "fraud":
                stat.fraud_txn = int((stat.fraud_txn or 0) + 1)
            stat.last_updated = __import__("datetime").datetime.utcnow()
            session.commit()
        except Exception:
            session.rollback()
    finally:
        session.close()

    return redirect(url_for("result", status=prediction_label, amount=amount, receiver=receiver, confidence=round(confidence, 3), high_risk=("1" if high_risk_flag else "0")))


@app.route("/result")
@user_required
def result(current_user):
    status = request.args.get("status", "safe")
    amount = request.args.get("amount", type=float)
    receiver = request.args.get("receiver")
    conf = request.args.get("confidence")
    high_risk = request.args.get("high_risk") == "1"
    return render_template("result.html", status=status, amount=amount, receiver=receiver, user=current_user, confidence=conf, high_risk=high_risk)


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("login"))


def send_otp_email(to_email: str, otp: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    if not all([smtp_host, smtp_user, smtp_pass]):
        return False
    msg = MIMEText(f"Your UPIGUARD OTP is: {otp}")
    msg['Subject'] = 'UPIGUARD OTP Verification'
    msg['From'] = smtp_user
    msg['To'] = to_email
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        # Fallback to UI notice; avoid crashing on DNS/network/auth errors
        return False


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
