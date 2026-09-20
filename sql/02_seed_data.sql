USE procureflow;

INSERT INTO materials (code, name, category, unit, safety_stock) VALUES
('MAT-1001', '工业温度传感器', '自动化元件', '个', 80),
('MAT-1002', 'PLC控制模块', '自动化元件', '台', 30),
('MAT-2001', '304不锈钢板', '原材料', '张', 120)
ON DUPLICATE KEY UPDATE name=VALUES(name), category=VALUES(category), unit=VALUES(unit), safety_stock=VALUES(safety_stock);

INSERT INTO inventory (material_id, warehouse, on_hand_qty, reserved_qty)
SELECT id, '上海一号仓', 260, 40 FROM materials WHERE code='MAT-1001'
ON DUPLICATE KEY UPDATE on_hand_qty=VALUES(on_hand_qty), reserved_qty=VALUES(reserved_qty);
INSERT INTO inventory (material_id, warehouse, on_hand_qty, reserved_qty)
SELECT id, '苏州备件仓', 65, 12 FROM materials WHERE code='MAT-1002'
ON DUPLICATE KEY UPDATE on_hand_qty=VALUES(on_hand_qty), reserved_qty=VALUES(reserved_qty);
INSERT INTO inventory (material_id, warehouse, on_hand_qty, reserved_qty)
SELECT id, '无锡原料仓', 140, 35 FROM materials WHERE code='MAT-2001'
ON DUPLICATE KEY UPDATE on_hand_qty=VALUES(on_hand_qty), reserved_qty=VALUES(reserved_qty);

INSERT INTO suppliers (code, name, rating, on_time_rate, status, contact_name, contact_phone) VALUES
('SUP-001', '华东智控科技', 4.80, 96.50, 'ACTIVE', '张经理', '13800000001'),
('SUP-002', '苏州联创自动化', 4.60, 98.20, 'ACTIVE', '李经理', '13800000002'),
('SUP-003', '沪工供应链', 4.90, 92.00, 'ACTIVE', '王经理', '13800000003')
ON DUPLICATE KEY UPDATE name=VALUES(name), rating=VALUES(rating), on_time_rate=VALUES(on_time_rate), status=VALUES(status);

INSERT INTO supplier_quotes (supplier_id, material_id, min_qty, unit_price, lead_time_days, valid_until)
SELECT s.id, m.id, 50, 128.00, 7, '2030-12-31' FROM suppliers s JOIN materials m WHERE s.code='SUP-001' AND m.code='MAT-1001'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price), lead_time_days=VALUES(lead_time_days), valid_until=VALUES(valid_until);
INSERT INTO supplier_quotes (supplier_id, material_id, min_qty, unit_price, lead_time_days, valid_until)
SELECT s.id, m.id, 100, 119.50, 12, '2030-12-31' FROM suppliers s JOIN materials m WHERE s.code='SUP-002' AND m.code='MAT-1001'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price), lead_time_days=VALUES(lead_time_days), valid_until=VALUES(valid_until);
INSERT INTO supplier_quotes (supplier_id, material_id, min_qty, unit_price, lead_time_days, valid_until)
SELECT s.id, m.id, 50, 124.00, 9, '2030-12-31' FROM suppliers s JOIN materials m WHERE s.code='SUP-003' AND m.code='MAT-1001'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price), lead_time_days=VALUES(lead_time_days), valid_until=VALUES(valid_until);

