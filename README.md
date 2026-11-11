<div align="center">

# TrueMoney Angpao API

**Open-source API for TrueMoney Gift Voucher claims**

Self-host it, run it in Docker, or deploy the Cloudflare Pages Worker. You choose the infrastructure.

[Releases](https://github.com/Namnarak/Truemoney-Angpao/releases) · [Issues](https://github.com/Namnarak/Truemoney-Angpao/issues) · [API Docs](#api)

</div>

---

## Overview

API สำหรับรับเงินจากลิงก์ซองของขวัญ TrueMoney (อั่งเปา) โดยผู้ใช้งานเลือกโครงสร้างพื้นฐานเองได้ โปรเจกต์นี้ไม่ต้องพึ่ง Server, Domain, API key หรือบัญชี Cloudflare ของผู้พัฒนา

### Deployment options

| วิธีติดตั้ง | Runtime | Transport |
|---|---|---|
| Docker / Docker Compose | Python + FastAPI | \`curl-cffi\` (Chrome TLS) พร้อม \`urllib\` fallback |
| VPS / Dedicated / Local | Python + FastAPI | \`curl-cffi\` (Chrome TLS) พร้อม \`urllib\` fallback |
| Cloudflare Pages | Cloudflare Worker | Native \`fetch()\` |

ทั้งสองแบบให้ API contract เดียวกัน (\`GET /api/{phone}/{voucher_id}\`, \`POST /api\`) แต่เป็น deployment แยกกัน ผู้ใช้เลือกได้ว่าจะใช้แบบไหน

## Quick start: Docker

ต้องมี Docker Engine และ Docker Compose Plugin

\`\`\`bash
git clone https://github.com/Namnarak/Truemoney-Angpao.git
cd Truemoney-Angpao
cp .env.example .env
docker compose up -d --build
\`\`\`

API จะอยู่ที่ \`http://localhost:8000\`

- Health: \`http://localhost:8000/health\`
- Interactive API docs: \`http://localhost:8000/docs\`
- Logs: \`docker compose logs -f\`

## Quick start: Python

ต้องใช้ Python 3.10 ขึ้นไป

\`\`\`bash
git clone https://github.com/Namnarak/Truemoney-Angpao.git
cd Truemoney-Angpao
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
\`\`\`

## Configuration

คัดลอก \`.env.example\` เป็น \`.env\` แล้วปรับค่าตามต้องการ

| Variable | Default | Description |
|---|---:|---|
| \`PORT\` | \`8000\` | Host port เมื่อใช้ Compose |
| \`TM_TRANSPORT\` | \`auto\` | \`auto\`, \`curl_cffi\` หรือ \`urllib\` |
| \`TM_CURL_IMPERSONATE\` | \`chrome\` | Browser profile ที่ curl-cffi ใช้ |
| \`TM_TIMEOUT\` | \`20\` | Upstream timeout (seconds) |
| \`TM_RATE_LIMIT\` | \`30\` | Requests per client ต่อช่วงเวลา |
| \`TM_RATE_WINDOW\` | \`60\` | Rate-limit window (seconds) |
| \`LOG_LEVEL\` | \`INFO\` | Python logging level |

\`auto\` จะเลือก curl-cffi ก่อน และใช้ urllib เมื่อไม่มี curl-cffi ติดตั้งอยู่ การเปลี่ยน transport ไม่ได้ทำให้ upstream ยอมรับทุก request หรือรับประกันว่าจะผ่านระบบป้องกันของ TrueMoney

## Cloudflare Pages deployment

ใช้บัญชี Cloudflare ของคุณเอง:

1. ติดตั้ง Node.js และ Wrangler: \`npm install -g wrangler\`
2. Login: \`wrangler login\`
3. จาก root ของ repository สั่ง \`wrangler pages deploy .\`
4. เลือก project ของคุณเองเมื่อ Wrangler ถาม

Cloudflare Worker ใช้ Native Fetch ตามข้อจำกัดของ Workers runtime; \`curl-cffi\` ใช้ได้เฉพาะ Python runtime เท่านั้น ไม่ต้องตั้งค่า secret ของผู้พัฒนา

## API

### POST /api

\`\`\`bash
curl -X POST http://localhost:8000/api \\
  -H 'Content-Type: application/json' \\
  -H 'Accept: application/json' \\
  -d '{"phone":"0812345678","voucher_id":"abc123xyz"}'
\`\`\`

Request body:

\`\`\`json
{
  "phone": "0812345678",
  "voucher_id": "abc123xyz"
}
\`\`\`

### GET /api/{phone}/{voucher_id}

\`\`\`bash
curl 'http://localhost:8000/api/0812345678/abc123xyz'
\`\`\`

ส่ง voucher URL แบบเต็มแทน voucher ID ได้เช่นกัน

### Health check

\`\`\`bash
curl http://localhost:8000/health
\`\`\`

### Success response

\`\`\`json
{
  "success": true,
  "status": 200,
  "message": "รับเงินสำเร็จ",
  "code": "SUCCESS",
  "data": {
    "name": "ผู้ส่ง",
    "amount": "10.00"
  }
}
\`\`\`

### Error response

\`\`\`json
{
  "success": false,
  "status": 400,
  "message": "ลิงค์ซองของขวัญหมดอายุ",
  "code": "VOUCHER_EXPIRED",
  "data": null
}
\`\`\`

## Important operational notes

- Claim requests เป็นการทำธุรกรรมจริง ตรวจสอบเบอร์โทรและ voucher ให้ถูกต้องก่อนส่ง
- **ไม่มี automatic retry** เมื่อ timeout หรือ connection หลุด เพราะ upstream อาจรับคำขอไปแล้วและผลลัพธ์ยังไม่ชัดเจน API จะคืน \`CLAIM_OUTCOME_UNKNOWN\`; ตรวจสอบสถานะก่อนลองใหม่
- Rate limit ของ Python deployment เป็น in-memory ต่อ process เหมาะกับ single instance; หาก scale หลาย replicas ให้ใส่ reverse proxy / shared rate limiter ของคุณเอง
- ใช้ HTTPS และตั้ง rate limiting / access controls ที่ edge หากเปิด API สู่สาธารณะ
- อย่า commit ไฟล์ \`.env\` หรือ credentials
- \`curl-cffi\` เป็น transport compatibility option ไม่ใช่การรับประกันการ bypass anti-bot หรือข้อจำกัดของ upstream
- การใช้งานขึ้นอยู่กับ availability, policy และเงื่อนไขของ TrueMoney

## License

See [LICENSE](LICENSE) if present. Contributions and bug reports are welcome via GitHub Issues.
