# TrueMoney Angpao Gateway API

> ⚡ Free to use • Cloudflare Pages • REST API • Version 1.0.0

TrueMoney Angpao Gateway เป็น REST API สำหรับรับเงินจากลิงก์ซองของขวัญ TrueMoney ผ่าน HTTP API โดยไม่ต้องล็อกอิน

## Features

* ⚡ ฟรี ไม่มีค่าใช้จ่าย
* ☁️ Deploy บน Cloudflare Pages
* 📦 ไม่ต้องล็อกอิน
* 🔒 รองรับ GET และ POST
* 📄 JSON Response
* 🛡️ Rate Limit 30 requests/minute
* 🆔 รองรับ `X-Request-ID`

---

# Base URL

```text
https://tmn-angpao.pages.dev/api
```

---

# Authentication

ไม่ต้องใช้ Authentication

---

# GET Endpoint

รับเงินผ่าน URL

```http
GET /api/{phone}/{voucher_id}
```

### Parameters

| Name         | Type   | Description                                       |
| ------------ | ------ | ------------------------------------------------- |
| `phone`      | string | เบอร์โทรศัพท์ผู้รับเงิน 10 หลัก เช่น `0812345678` |
| `voucher_id` | string | รหัสซองของขวัญ (ค่าหลัง `?v=`)                    |

ตัวอย่าง

```
https://gift.truemoney.com/campaign/?v=abc123xyz
```

ใช้

```
abc123xyz
```

### Example

```bash
curl "https://tmn-angpao.pages.dev/api/0812345678/abc123xyz"
```

หรือ

```
https://tmn-angpao.pages.dev/api/0812345678/abc123xyz
```

---

# POST Endpoint

ส่งข้อมูลผ่าน JSON

```http
POST /api
```

## Headers

```http
Content-Type: application/json
Accept: application/json
```

## Request Body

```json
{
  "phone": "0812345678",
  "voucher_id": "abc123xyz"
}
```

## Example

```bash
curl -X POST "https://tmn-angpao.pages.dev/api" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "phone":"0812345678",
    "voucher_id":"abc123xyz"
}'
```

---

# Response Headers

| Header        | Description                           |
| ------------- | ------------------------------------- |
| Content-Type  | `application/json; charset=utf-8`     |
| Cache-Control | `no-store, no-cache, must-revalidate` |
| X-Request-ID  | ใช้อ้างอิงเวลาติดต่อ Support          |
| Retry-After   | แสดงเมื่อเกิด Rate Limit              |

---

# Success Response

```json
{
  "success": true,
  "status": 200,
  "message": "รับเงินสำเร็จ",
  "code": "SUCCESS",
  "data": {
    "name": "นาย ทดสอบ ***",
    "amount": "10.00"
  }
}
```

---

# Rate Limited

HTTP Status

```
429 Too Many Requests
```

Header

```
Retry-After: 30
```

Response

```json
{
  "success": false,
  "status": 429,
  "message": "ยิงคำขอเร็วเกินไป กรุณารอสักครู่",
  "code": "RATE_LIMITED",
  "data": null
}
```

---

# Error Example

```json
{
  "success": false,
  "status": 400,
  "message": "ลิงค์ซองของขวัญหมดอายุ",
  "code": "VOUCHER_EXPIRED",
  "data": null
}
```

---

# HTTP Status Codes

| Status | Description            |
| ------ | ---------------------- |
| 200    | Success                |
| 400    | Bad Request            |
| 404    | Not Found              |
| 405    | Method Not Allowed     |
| 415    | Unsupported Media Type |
| 429    | Too Many Requests      |
| 500    | Internal Server Error  |

---

# Error Codes

| HTTP | Code                      | Description                                           |
| ---- | ------------------------- | ----------------------------------------------------- |
| 200  | SUCCESS                   | รับเงินสำเร็จ                                         |
| 400  | VOUCHER_EXPIRED           | ลิงก์ซองของขวัญหมดอายุ                                |
| 400  | VOUCHER_ALREADY_USED      | ลิงก์ซองของขวัญถูกใช้งานแล้ว                          |
| 400  | SELF_CLAIM_NOT_ALLOWED    | ไม่สามารถใช้อั่งเปาของตัวเองได้                       |
| 400  | INVALID_PHONE_OR_USED     | เบอร์รับเงินไม่ถูกต้อง หรือรับเงินไปแล้ว              |
| 400  | INVALID_PHONE             | เบอร์โทรไม่ถูกต้อง (ต้องมี 10 หลัก และขึ้นต้นด้วย 0)  |
| 400  | INVALID_VOUCHER           | กรุณาระบุลิงก์ซองของขวัญ                              |
| 400  | MISSING_PARAMETER         | กรุณาระบุ `phone` และ `voucher_id`                    |
| 400  | INVALID_PATH              | รูปแบบ URL ไม่ถูกต้อง ใช้ `/api/{phone}/{voucher_id}` |
| 400  | INVALID_JSON              | JSON Payload ไม่ถูกต้อง                               |
| 404  | VOUCHER_NOT_FOUND         | ไม่พบลิงก์ซองของขวัญ                                  |
| 405  | METHOD_NOT_ALLOWED        | รองรับเฉพาะ GET และ POST                              |
| 415  | UNSUPPORTED_MEDIA_TYPE    | Content-Type ต้องเป็น `application/json`              |
| 429  | RATE_LIMITED              | ส่งคำขอเร็วเกินไป กรุณารอ 30 วินาที                   |
| 500  | INTERNAL_SERVER_ERROR     | เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์                        |
| 500  | EXTERNAL_SERVER_ERROR     | ระบบภายนอกขัดข้อง                                     |
| 500  | EXTERNAL_INVALID_RESPONSE | ระบบภายนอกตอบกลับไม่ถูกต้อง                           |

---

# Rate Limit

```
30 requests / minute / IP
```

เมื่อเกินกำหนด API จะตอบกลับ

```
HTTP 429 Too Many Requests
```

พร้อม Header

```
Retry-After: 30
```

---

# Project Information

| Item     | Value            |
| -------- | ---------------- |
| Version  | 1.0.0            |
| Runtime  | Cloudflare Pages |
| Protocol | HTTP / HTTPS     |
| Response | JSON             |
| Methods  | GET, POST        |
| License  | Free to use      |

---

## Powered by Cytech Team

Made with ❤️ by **p.namnarak**

Version **1.0.0** • 2026
