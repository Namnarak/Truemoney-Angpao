import unittest
from app.main import normalize_voucher, map_upstream

class VoucherNormalizationTests(unittest.TestCase):
    def test_accepts_hash(self):
        self.assertEqual(normalize_voucher("abc123xyz"), "abc123xyz")

    def test_extracts_hash_from_official_url(self):
        self.assertEqual(
            normalize_voucher("https://gift.truemoney.com/campaign/?v=abc123xyz"),
            "abc123xyz",
        )

    def test_rejects_untrusted_url(self):
        self.assertEqual(normalize_voucher("https://example.com/?v=abc123"), "")

class UpstreamMappingTests(unittest.TestCase):
    def test_success_shape(self):
        result = map_upstream(200, {
            "success": True,
            "data": {"name": "Sender", "amount": "10.00"},
        })
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'"code":"SUCCESS"', result.body)

    def test_expired_voucher(self):
        result = map_upstream(400, {
            "status": {"code": "VOUCHER_EXPIRED", "message": "expired"},
        })
        self.assertEqual(result.status_code, 400)
        self.assertIn(b'"code":"VOUCHER_EXPIRED"', result.body)

if __name__ == "__main__":
    unittest.main()
