// _worker.js
// TrueMoney Angpao Claim API — Powered by Cytech Team
// Cloudflare Pages Advanced Mode — serves static + API

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const pathname = url.pathname;
    const method = request.method;

    // --- Generate Request ID for tracing ---
    const requestId = generateRequestId();

    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Request-ID',
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'X-Request-ID': requestId,
    };

    // --- OPTIONS preflight ---
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // --- Route: static assets (HTML, CSS, JS) ---
    if (!pathname.startsWith('/api')) {
      return env.ASSETS.fetch(request);
    }

    let phone, voucherId;

    try {
      // --- Method validation ---
      if (method !== 'GET' && method !== 'POST') {
        return jsonResponse(false, 405, 'Method Not Allowed', 'METHOD_NOT_ALLOWED', null, corsHeaders);
      }

      // --- Parse input ---
      if (method === 'GET') {
        // /api/{phone}/{voucher_id}
        const pathAfterApi = request.url.split('/api/')[1] || '';
        const firstSlashIdx = pathAfterApi.indexOf('/');
        
        if (firstSlashIdx === -1 || firstSlashIdx === 0) {
          return jsonResponse(
            false,
            400,
            'รูปแบบ URL ไม่ถูกต้อง ใช้ /api/{phone}/{voucher_id}',
            'INVALID_PATH',
            null,
            corsHeaders
          );
        }
        
        phone = pathAfterApi.substring(0, firstSlashIdx);
        voucherId = pathAfterApi.substring(firstSlashIdx + 1);
        
        try {
          voucherId = decodeURIComponent(voucherId);
        } catch(e) {}
      } else if (method === 'POST') {
        // --- Check Content-Type before parsing ---
        const contentType = request.headers.get('Content-Type') || '';
        if (!contentType.includes('application/json')) {
          return jsonResponse(
            false,
            415,
            'Content-Type ต้องเป็น application/json',
            'UNSUPPORTED_MEDIA_TYPE',
            null,
            corsHeaders
          );
        }

        let body;
        try {
          body = await request.json();
        } catch (_) {
          return jsonResponse(
            false,
            400,
            'JSON payload ไม่ถูกต้อง',
            'INVALID_JSON',
            null,
            corsHeaders
          );
        }

        phone = body.phone?.toString().trim();
        voucherId = body.voucher_id?.toString().trim();

        if (!phone || !voucherId) {
          return jsonResponse(
            false,
            400,
            'กรุณาระบุ phone และ voucher_id',
            'MISSING_PARAMETER',
            null,
            corsHeaders
          );
        }
      }

      // --- Validate phone ---
      if (!/^0\d{9}$/.test(phone)) {
        return jsonResponse(
          false,
          400,
          'เบอร์รับเงินไม่ถูกต้อง (ต้อง 10 หลัก ขึ้นต้นด้วย 0)',
          'INVALID_PHONE',
          null,
          corsHeaders
        );
      }

      // --- Validate voucher ---
      if (!voucherId || voucherId.trim().length === 0) {
        return jsonResponse(
          false,
          400,
          'กรุณาระบุลิงค์ซองของขวัญ',
          'INVALID_VOUCHER',
          null,
          corsHeaders
        );
      }

      // Extract voucher hash if full URL is provided
      const vMatch = voucherId.match(/[?&]v=([^&#]+)/);
      if (vMatch) {
        voucherId = vMatch[1];
      }

      // ================================================================
      //  CLAIM LOGIC — ติดต่อ TrueMoney โดยตรง
      // ================================================================

      const claimUrl = `https://gift.truemoney.com/campaign/vouchers/${voucherId}/redeem`;

      const claimBody = JSON.stringify({
        mobile: phone,
        voucher_hash: voucherId
      });

      const claimResp = await fetch(claimUrl, {
        method: 'POST',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Linux; Android 12; POCO X3 GT) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
          'Content-Type': 'application/json',
          'Origin': 'https://gift.truemoney.com',
          'Referer': `https://gift.truemoney.com/campaign/?v=${voucherId}`,
        },
        body: claimBody,
        redirect: 'follow',
      });

      // --- Step 4: อ่าน response ---
      let claimData;
      try {
        claimData = await claimResp.json();
      } catch (_) {
        console.error(`[ENI] [${requestId}] Invalid JSON from claim endpoint:`, claimResp.status);
        return jsonResponse(
          false,
          500,
          'เซิร์ฟเวอร์ภายนอกตอบกลับมาไม่ถูกต้อง',
          'EXTERNAL_INVALID_RESPONSE',
          null,
          corsHeaders
        );
      }

      // --- Step 5: แปลงผลลัพธ์ ---
      const isSuccess = (
        claimData.status === 'success' ||
        claimData.success === true ||
        claimData.data?.status === 'success' ||
        claimData.status?.code === 'SUCCESS'
      );

      if (isSuccess) {
        return jsonResponse(true, 200, 'รับเงินสำเร็จ', 'SUCCESS', {
          name: claimData.sender_name || claimData.data?.name || claimData.data?.owner_profile?.full_name || claimData.data?.voucher_owner_profile?.full_name || 'ไม่ระบุชื่อ',
          amount: claimData.amount || claimData.data?.amount || claimData.data?.my_ticket?.amount_baht || '0.00'
        }, corsHeaders);
      }

      // --- Step 6: จัดการ error ตามประเภท ---
      const rawCode = claimData.status?.code || claimData.code || '';
      const errorMsg = claimData.status?.message || claimData.message || claimData.error || 'ไม่สามารถรับเงินได้';
      let statusCode = 400;
      let finalMessage = errorMsg;
      let errorCode = rawCode || 'CLAIM_FAILED';

      if (rawCode === 'VOUCHER_EXPIRED' || errorMsg.includes('หมดอายุ') || errorMsg.includes('expired')) {
        statusCode = 400;
        finalMessage = 'ลิงค์ซองของขวัญหมดอายุ';
        errorCode = 'VOUCHER_EXPIRED';
      } else if (rawCode === 'VOUCHER_OUT_OF_STOCK' || errorMsg.includes('ถูกใช้งานแล้ว') || errorMsg.includes('already')) {
        statusCode = 400;
        finalMessage = 'ลิงค์ซองของขวัญถูกใช้งานแล้วทั้งหมด';
        errorCode = 'VOUCHER_ALREADY_USED';
      } else if (rawCode === 'TARGET_USER_REDEEMED' || errorMsg.includes('redeeming') || errorMsg.includes('redeemed')) {
        statusCode = 400;
        finalMessage = 'คุณรับเงินจากซองนี้ไปแล้ว';
        errorCode = 'TARGET_USER_REDEEMED';
      } else if (rawCode === 'TARGET_USER_NOT_FOUND' || errorMsg.includes('ตัวเอง') || errorMsg.includes('self')) {
        statusCode = 400;
        finalMessage = 'ไม่สามารถใช้อั่งเปาของตัวเองได้ หรือไม่พบผู้ใช้';
        errorCode = 'SELF_CLAIM_NOT_ALLOWED';
      } else if (rawCode === 'VOUCHER_NOT_FOUND' || errorMsg.includes('exist') || claimResp.status === 404) {
        statusCode = 404;
        finalMessage = 'ไม่พบลิงค์ซองของขวัญ';
        errorCode = 'VOUCHER_NOT_FOUND';
      } else if (errorMsg.includes('เบอร์') || errorMsg.includes('mobile')) {
        statusCode = 400;
        finalMessage = 'เบอร์รับเงินนี้ไม่ถูกต้อง หรือรับเงินไปแล้ว';
        errorCode = 'INVALID_PHONE_OR_USED';
      } else if (claimResp.status === 429) {
        statusCode = 429;
        finalMessage = 'ยิงคำขอเร็วเกินไป กรุณารอสักครู่';
        errorCode = 'RATE_LIMITED';
      } else if (claimResp.status >= 500) {
        statusCode = 500;
        finalMessage = 'เซิร์ฟเวอร์ภายนอกขัดข้อง กรุณาลองใหม่ภายหลัง';
        errorCode = 'EXTERNAL_SERVER_ERROR';
      }

      // ถ้าเป็น 429 → ส่ง Retry-After
      const extraHeaders = { ...corsHeaders };
      if (statusCode === 429) {
        extraHeaders['Retry-After'] = '30';
      }

      return jsonResponse(false, statusCode, finalMessage, errorCode, null, extraHeaders);

    } catch (err) {
      // --- Error ที่ไม่คาดคิด ---
      console.error(`[ENI] [${requestId}] Unhandled error:`, err.message, err.stack);

      return jsonResponse(
        false,
        500,
        'เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์',
        'INTERNAL_SERVER_ERROR',
        null,
        corsHeaders
      );
    }
  }
};

// ================================================================
//  Helper: สร้าง Response แบบ JSON สม่ำเสมอ
// ================================================================
function jsonResponse(success, status, message, code, data, headers) {
  const body = JSON.stringify({
    success,
    status,
    message,
    code: code || null,
    data: data || null,
  });

  return new Response(body, {
    status,
    headers: {
      ...headers,
      'Content-Type': 'application/json; charset=utf-8',
    },
  });
}

// ================================================================
//  Helper: สร้าง Request ID
// ================================================================
function generateRequestId() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < 12; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}
