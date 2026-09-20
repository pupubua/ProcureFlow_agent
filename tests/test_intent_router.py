import unittest

from ProcureFlow.intent_router import RuleBasedIntentRouter
from ProcureFlow.schemas import Intent


class IntentRouterTests(unittest.TestCase):
    def setUp(self):
        self.router = RuleBasedIntentRouter()

    def test_combined_inventory_and_supplier_query(self):
        decision = self.router.route("查询 MAT-1001 库存，并比较采购 100 件的供应商报价")
        self.assertIn(Intent.INVENTORY, decision.intents)
        self.assertIn(Intent.SUPPLIER, decision.intents)
        self.assertEqual(decision.entities["material_code"], "MAT-1001")
        self.assertEqual(decision.entities["quantity"], 100)

    def test_purchase_order_requires_confirmation(self):
        decision = self.router.route("为 MAT-1001 创建采购单，采购 100 件")
        self.assertIn(Intent.PURCHASE_ORDER, decision.intents)
        self.assertTrue(decision.needs_confirmation)

    def test_status_extracts_po_number(self):
        decision = self.router.route("查询 PO2026092000123 的订单状态")
        self.assertIn(Intent.ORDER_STATUS, decision.intents)
        self.assertEqual(decision.entities["po_no"], "PO2026092000123")


if __name__ == "__main__":
    unittest.main()

