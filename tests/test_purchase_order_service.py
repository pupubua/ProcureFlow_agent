import unittest

from ProcureFlow.services import PurchaseOrderService


class FakeOrderRepository:
    def __init__(self):
        self.calls = []

    def create_order(self, **payload):
        self.calls.append(payload)
        return {"created": True, "po_no": "PO2099010100001"}


class PurchaseOrderServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeOrderRepository()
        self.service = PurchaseOrderService(self.repo)
        self.payload = {
            "requester": "张三",
            "supplier_id": 1,
            "material_code": "MAT-1001",
            "quantity": 100,
            "unit_price": 128.0,
            "expected_date": "2099-12-31",
            "idempotency_key": "test-key-001",
        }

    def test_requires_human_confirmation(self):
        result = self.service.create(confirmed=False, **self.payload)
        self.assertEqual(result["reason"], "confirmation_required")
        self.assertEqual(self.repo.calls, [])

    def test_confirmed_order_calls_repository(self):
        result = self.service.create(confirmed=True, **self.payload)
        self.assertTrue(result["created"])
        self.assertEqual(len(self.repo.calls), 1)

    def test_missing_fields_are_reported(self):
        payload = dict(self.payload)
        del payload["supplier_id"]
        result = self.service.create(confirmed=True, **payload)
        self.assertEqual(result["missing_fields"], ["supplier_id"])


if __name__ == "__main__":
    unittest.main()

