from __future__ import annotations
import json, logging, os, re, time, urllib.error, urllib.request
from collections import defaultdict, deque
from typing import Any
from urllib.parse import quote, unquote, urlparse, parse_qs
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

APP_VERSION = "2.1.0"
UPSTREAM = "https://gift.truemoney.com"
TRANSPORT = os.getenv("TM_TRANSPORT", "auto").lower()
TIMEOUT = float(os.getenv("TM_TIMEOUT", "20"))
RATE_LIMIT = int(os.getenv("TM_RATE_LIMIT", "30"))
RATE_WINDOW = int(os.getenv("TM_RATE_WINDOW", "60"))
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("truemoney-angpao")
app = FastAPI(title="TrueMoney Angpao API", version=APP_VERSION)
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)

def response(success: bool, status: int, message: str, code: str, data: Any = None, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse({"success": success, "status": status, "message": message, "code": code, "data": data}, status_code=status, headers=headers or {})

def normalize_voucher(value: str) -> str:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if parsed.hostname not in {"gift.truemoney.com", "www.gift.truemoney.com"}:
            return ""
        value = parse_qs(parsed.query).get("v", [""])[0]
    else:
        value = unquote(value)
    return value.strip()

def rate_limited(key: str) -> bool:
    now = time.monotonic()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] >= RATE_WINDOW:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        return True
    bucket.append(now)
    return False

def post_claim(phone: str, voucher_id: str) -> tuple[int, dict[str, Any]]:
    url = f"{UPSTREAM}/campaign/vouchers/{quote(voucher_id, safe='')}/redeem"
    body = json.dumps({"mobile": phone, "voucher_hash": voucher_id}).encode()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*", "Content-Type": "application/json",
        "Origin": UPSTREAM, "Referer": f"{UPSTREAM}/campaign/?v={quote(voucher_id)}",
    }
    if TRANSPORT not in {"auto", "curl_cffi", "urllib"}:
        raise RuntimeError("TM_TRANSPORT must be auto, curl_cffi, or urllib")
    if TRANSPORT == "curl_cffi" and curl_requests is None:
        raise RuntimeError("curl-cffi is required when TM_TRANSPORT=curl_cffi")
    if TRANSPORT in {"auto", "curl_cffi"} and curl_requests is not None:
        result = curl_requests.post(url, data=body, headers=headers, timeout=TIMEOUT,
            impersonate=os.getenv("TM_CURL_IMPERSONATE", "chrome"), allow_redirects=True)
        try:
            payload = result.json()
        except Exception:
            payload = {}
        return result.status_code, payload if isinstance(payload, dict) else {}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as result:
            raw, status = result.read(), result.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    payload = json.loads(raw.decode("utf-8"))
    return status, payload if isinstance(payload, dict) else {}

def map_upstream(status: int, payload: dict[str, Any]) -> JSONResponse:
    state = payload.get("status")
    raw_code = (state.get("code") if isinstance(state, dict) else None) or payload.get("code") or ""
    message = (state.get("message") if isinstance(state, dict) else None) or payload.get("message") or payload.get("error") or "ไม่สามารถรับเงินได้"
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    success = state == "success" or payload.get("success") is True or data.get("status") == "success" or raw_code == "SUCCESS"
    if success:
        owner = data.get("owner_profile") or data.get("voucher_owner_profile") or {}
        ticket = data.get("my_ticket") or {}
        return response(True, 200, "รับเงินสำเร็จ", "SUCCESS", {
            "name": payload.get("sender_name") or data.get("name") or owner.get("full_name") or "ไม่ระบุชื่อ",
            "amount": payload.get("amount") or data.get("amount") or ticket.get("amount_baht") or "0.00"})
    text = str(message).lower()
    if raw_code == "VOUCHER_EXPIRED" or "หมดอายุ" in text or "expired" in text:
        return response(False, 400, "ลิงค์ซองของขวัญหมดอายุ", "VOUCHER_EXPIRED")
    if raw_code in {"VOUCHER_OUT_OF_STOCK", "VOUCHER_ALREADY_USED"} or "already" in text or "ถูกใช้งานแล้ว" in text:
        return response(False, 400, "ลิงค์ซองของขวัญถูกใช้งานแล้ว", "VOUCHER_ALREADY_USED")
    if raw_code == "TARGET_USER_REDEEMED" or "redeemed" in text:
        return response(False, 400, "คุณรับเงินจากซองนี้ไปแล้ว", "TARGET_USER_REDEEMED")
    if raw_code == "TARGET_USER_NOT_FOUND" or "ตัวเอง" in text or "self" in text:
        return response(False, 400, "ไม่สามารถใช้อั่งเปาของตัวเองได้ หรือไม่พบผู้ใช้", "SELF_CLAIM_NOT_ALLOWED")
    if raw_code == "VOUCHER_NOT_FOUND" or status == 404:
        return response(False, 404, "ไม่พบลิงค์ซองของขวัญ", "VOUCHER_NOT_FOUND")
    if "เบอร์" in text or "mobile" in text:
        return response(False, 400, "เบอร์รับเงินนี้ไม่ถูกต้อง หรือรับเงินไปแล้ว", "INVALID_PHONE_OR_USED")
    if status == 429:
        return response(False, 429, "ยิงคำขอเร็วเกินไป กรุณารอสักครู่", "RATE_LIMITED", headers={"Retry-After": "30"})
    if status >= 500:
        return response(False, 502, "เซิร์ฟเวอร์ภายนอกขัดข้อง", "EXTERNAL_SERVER_ERROR")
    return response(False, 400, str(message), str(raw_code or "CLAIM_FAILED"))

async def handle_claim(request: Request, phone: str | None, voucher: str | None) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID") or os.urandom(6).hex()
    if not phone or not voucher:
        return response(False, 400, "กรุณาระบุ phone และ voucher_id", "MISSING_PARAMETER", headers={"X-Request-ID": request_id})
    phone, voucher_id = str(phone).strip(), normalize_voucher(str(voucher))
    if not re.fullmatch(r"0\d{9}", phone):
        return response(False, 400, "เบอร์รับเงินไม่ถูกต้อง (ต้อง 10 หลัก ขึ้นต้นด้วย 0)", "INVALID_PHONE", headers={"X-Request-ID": request_id})
    if not voucher_id or len(voucher_id) > 256:
        return response(False, 400, "กรุณาระบุลิงค์ซองของขวัญที่ถูกต้อง", "INVALID_VOUCHER", headers={"X-Request-ID": request_id})
    if rate_limited(request.client.host if request.client else "unknown"):
        return response(False, 429, "ยิงคำขอเร็วเกินไป กรุณารอสักครู่", "RATE_LIMITED", headers={"Retry-After": "30", "X-Request-ID": request_id})
    try:
        status, payload = post_claim(phone, voucher_id)
        result = map_upstream(status, payload)
        result.headers["X-Request-ID"] = request_id
        result.headers["Cache-Control"] = "no-store"
        return result
    except Exception as exc:
        # A timeout can happen after the upstream has received the claim. Never retry automatically.
        logger.warning("request_id=%s upstream transport failed (%s)", request_id, type(exc).__name__)
        return response(False, 502, "ไม่สามารถยืนยันผลจาก TrueMoney ได้ กรุณาตรวจสอบสถานะก่อนลองใหม่", "CLAIM_OUTCOME_UNKNOWN", headers={"X-Request-ID": request_id, "Cache-Control": "no-store"})

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}

@app.get("/api/{phone}/{voucher_id:path}")
async def claim_get(request: Request, phone: str, voucher_id: str) -> JSONResponse:
    return await handle_claim(request, phone, voucher_id)

@app.post("/api")
async def claim_post(request: Request) -> JSONResponse:
    if "application/json" not in request.headers.get("content-type", "").lower():
        return response(False, 415, "Content-Type ต้องเป็น application/json", "UNSUPPORTED_MEDIA_TYPE")
    try:
        body = await request.json()
    except Exception:
        return response(False, 400, "JSON payload ไม่ถูกต้อง", "INVALID_JSON")
    if not isinstance(body, dict):
        return response(False, 400, "JSON payload ต้องเป็น object", "INVALID_JSON")
    return await handle_claim(request, body.get("phone"), body.get("voucher_id"))

@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "TrueMoney Angpao API", "docs": "/docs", "health": "/health"}
