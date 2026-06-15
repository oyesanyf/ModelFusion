import unittest
from core.result_schema import UnifiedResult, coerce_unified


class TestResultSchema(unittest.TestCase):
    def test_unified_direct(self):
        r = UnifiedResult(success=True, content="ok", models_used=["m"])
        self.assertTrue(r.success)
        self.assertEqual(r.content, "ok")
        self.assertEqual(r.models_used, ["m"])

    def test_coerce_dict(self):
        raw = {"success": True, "content": "x", "models_used": ["a"], "insights": ["i"]}
        r = coerce_unified(raw)
        self.assertTrue(r.success)
        self.assertEqual(r.content, "x")
        self.assertEqual(r.models_used, ["a"])
        self.assertEqual(r.insights, ["i"])

    def test_coerce_object_like(self):
        class Obj:
            success = False
            content = "err"
            processing_time_ms = 12.3
        r = coerce_unified(Obj())
        self.assertFalse(r.success)
        self.assertEqual(r.content, "err")
        self.assertGreaterEqual(r.processing_time_ms, 12.3)


if __name__ == '__main__':
    unittest.main()


