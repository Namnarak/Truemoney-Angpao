# TrueMoney Angpao API (v2.0.0)

API สำหรับรับเงินจากลิงก์ซองของขวัญ TrueMoney (อั่งเปา) ได้โดยตรง ทำงานแบบเรียลไทม์ และไม่ต้องล็อกอิน (ใช้ Cloudflare Workers เป็นตัวกลาง)

## คุณสมบัติ
- **เวอร์ชัน**: 2.0.0
- **การเชื่อมต่อ**: รองรับทั้ง `GET` และ `POST`
- **อัตราการใช้งาน**: 30 Requests / นาที (Rate Limited)
- **การป้อนข้อมูล**: รหัสซอง (`voucher_id`) รองรับทั้งรหัสสั้นๆ (เช่น `abc123xyz`) หรือจะส่งเป็นลิงก์เต็มมาก็ได้เลย

---

## 🔹 1. GET Method
เหมาะสำหรับการเรียกใช้งานง่ายๆ ผ่าน URL โดยตรง (เช่น ทำผ่านเว็บบราวเซอร์ หรือบอท Discord)

**Endpoint:**
```http
GET https://tmn-angpao.pages.dev/api/{phone}/{voucher_id}
```

**พารามิเตอร์:**
- `phone`: เบอร์โทรศัพท์ 10 หลักของผู้รับเงิน (เช่น `0812345678`)
- `voucher_id`: รหัสซองของขวัญ หรือลิงก์เต็มก็ได้

**ตัวอย่าง (GET):**
```bash
curl -X GET "https://tmn-angpao.pages.dev/api/0812345678/abc123xyz"
```

---

## 🔸 2. POST Method
เหมาะสำหรับการเชื่อมต่อที่ปลอดภัยและเป็นระบบมากกว่า ส่งข้อมูลผ่าน JSON Body

**Endpoint:**
```http
POST https://tmn-angpao.pages.dev/api
```

**Request Headers:**
- `Content-Type: application/json` (จำเป็น)
- `Accept: application/json` (แนะนำ)

**Request Body (JSON):**
```json
{
  "phone": "0812345678",
  "voucher_id": "abc123xyz"
}
```

**ตัวอย่าง (POST):**
```bash
curl -X POST "https://tmn-angpao.pages.dev/api" \
  -H "Content-Type: application/json" \
  -d '{"phone":"0812345678","voucher_id":"abc123xyz"}'
```

---

## 📤 ตัวอย่าง Response

**✅ สำเร็จ (200 OK)**
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

**❌ ผิดพลาด (ตัวอย่าง 400 Bad Request)**
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

## ⚠️ ตาราง Error Codes

| HTTP Status | Code | ข้อความ |
| :--- | :--- | :--- |
| **200** | `SUCCESS` | รับเงินสำเร็จ ✅ |
| **400** | `VOUCHER_EXPIRED` | ลิงค์ซองของขวัญหมดอายุ |
| **400** | `VOUCHER_ALREADY_USED` | ลิงค์ซองของขวัญถูกใช้งานแล้ว |
| **400** | `SELF_CLAIM_NOT_ALLOWED` | ไม่สามารถใช้อั่งเปาของตัวเองได้ |
| **400** | `TARGET_USER_REDEEMED` | เป้าหมายรับซองไปแล้ว / หรือไม่ใช่ผู้รับที่กำหนด |
| **400** | `INVALID_PHONE_OR_USED` | เบอร์รับเงินนี้ไม่ถูกต้อง หรือรับเงินไปแล้ว |
| **400** | `INVALID_PHONE` | เบอร์รับเงินไม่ถูกต้อง (ต้อง 10 หลัก) |
| **400** | `INVALID_VOUCHER` | กรุณาระบุลิงค์ซองของขวัญ |
| **400** | `MISSING_PARAMETER` | กรุณาระบุ phone และ voucher_id |
| **404** | `VOUCHER_NOT_FOUND` | ไม่พบลิงค์ซองของขวัญ |
| **429** | `RATE_LIMITED` | ยิงคำขอเร็วเกินไป กรุณารอสักครู่ (Retry-After: 30) |
| **500** | `INTERNAL_SERVER_ERROR`| เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์ |
| **500** | `EXTERNAL_SERVER_ERROR`| เซิร์ฟเวอร์ภายนอก (TrueMoney) ขัดข้อง |

---

*Powered by Cytech Team | Version 2.0.0*
