import unittest

from ProcureFlow.security import UnsafeSQL, validate_readonly_sql


class ReadOnlySQLTests(unittest.TestCase):
    def test_allows_select_and_adds_limit(self):
        sql = validate_readonly_sql(
            "SELECT m.code FROM materials m JOIN inventory i ON i.material_id=m.id",
            {"materials", "inventory"},
        )
        self.assertTrue(sql.endswith("LIMIT 100"))

    def test_caps_large_limit(self):
        sql = validate_readonly_sql(
            "SELECT * FROM supplier_quotes LIMIT 999",
            {"supplier_quotes"},
        )
        self.assertTrue(sql.endswith("LIMIT 100"))

    def test_rejects_write_and_comments(self):
        with self.assertRaises(UnsafeSQL):
            validate_readonly_sql("DELETE FROM inventory", {"inventory"})
        with self.assertRaises(UnsafeSQL):
            validate_readonly_sql("SELECT * FROM inventory -- bypass", {"inventory"})

    def test_rejects_non_allowlisted_table(self):
        with self.assertRaises(UnsafeSQL):
            validate_readonly_sql("SELECT * FROM users", {"inventory"})


if __name__ == "__main__":
    unittest.main()

