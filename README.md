# ProcureFlow 企业采购与供应链多智能体协同平台

ProcureFlow 面向制造企业的间接物料与生产物料采购场景，把“查库存—询报价—比供应商—建采购单”拆成 3 个边界清晰的领域 Agent。总控通过 A2A 协议分发任务，各 Agent 再通过 MCP 调用数据库工具；所有写操作都经过人工确认、事务校验与幂等控制。

## 项目亮点

- **业务完整**：数据模型包含物料、分仓库存、供应商、有效报价、采购单、明细、库存占用和审计日志。
- **多 Agent 协作有依赖关系**：采购订单 Agent 下单前，会并行向库存 Agent 和供应商 Agent 二次核验。
- **读写隔离**：查询使用结构化参数；如扩展 Text-to-SQL，可复用 `security.py` 的单条 SELECT、表白名单、行数上限校验。订单写入只允许参数化领域服务。
- **采购安全机制**：人工确认、幂等键、有效报价与阶梯价检查、事务回滚、审计日志。
- **工程化**：FastAPI 接口、Streamlit 页面、环境变量、日志、定时同步、Docker MySQL、单元测试。

## 系统结构

```text
Streamlit / FastAPI
        |
        v
ProcureFlowOrchestrator (LLM 意图识别 + 规则降级)
        |
        +--A2A--> InventoryQueryAgent ----MCP----> InventoryService
        +--A2A--> SupplierQuoteAgent -----MCP----> SupplierService
        +--A2A--> PurchaseOrderAgent -----MCP----> PurchaseOrderService
                         |  A2A pre-checks        |
                         +------------------------+--> MySQL
```

端口约定：库存 MCP `8001`、供应商 MCP `8002`、采购单 MCP `8003`；库存 Agent `5005`、供应商 Agent `5006`、采购单 Agent `5007`；FastAPI `9000`、Streamlit `8501`。

## 采购业务常识（面试建议重点掌握）

1. **在库量、占用量、可用量**：可用量 = 在库量 - 已占用量。下单或领料不能只看账面在库量。
2. **安全库存**：用于吸收需求和交期波动。低于安全库存并不等于立即下单，还要结合在途量、采购提前期和未来需求。
3. **供应商选择不是只看最低价**：本项目同时返回报价、最小起订量、交期、评级和准时交付率。真实业务还会考虑质量合格率、账期、产能与风险。
4. **报价有效期与阶梯价**：同一供应商对不同采购量可能有不同报价，过期报价不能用于下单。
5. **采购单状态**：待审批 → 已审批 → 已发送 → 部分收货 → 已收货。创建采购单不会扣减现有库存，收货过账后才增加在库量；取消与变更要保留审计记录。
6. **三单匹配**：企业付款前通常核对采购订单、收货单和发票。当前版本覆盖采购订单，收货与发票可作为后续扩展。
7. **职责分离**：申请、审批、下单、收货和付款不应由同一角色完全控制；因此系统不允许 LLM 绕过人工确认直接写库。

## 快速启动

要求：Python 3.11+、Docker Desktop。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d mysql
python -m ProcureFlow.run_all
```

另开一个终端启动页面：

```powershell
.venv\Scripts\Activate.ps1
python -m streamlit run ProcureFlow/app.py --server.port 8501
```

如果 `.env` 中不配置 `OPENAI_API_KEY`，系统仍可用规则路由处理库存、报价和订单状态等基本意图；配置后启用 LLM 实体抽取与汇总。

## 可演示问题

- `查询 MAT-1001 的库存，并比较采购 100 件的供应商报价`
- `哪些物料低于安全库存？`
- `比较 MAT-1001 采购 100 件时的价格、交期和准时交付率`
- `查询 PO2026092000123 的订单状态`
- 完整下单需提供申请人、供应商 ID、物料编码、数量、单价、期望交期，并在页面勾选确认。

## 测试

```powershell
python -m compileall ProcureFlow tests
python -m unittest discover -s tests -v
```

单元测试覆盖只读 SQL 防护、组合意图识别、订单人工确认与字段校验。端到端运行前需要先启动 MySQL、MCP 和 A2A 服务。

## 面试时如何讲项目边界

- 当前项目是可运行的教学/作品集版本，供应商报价通过 JSON 模拟 SRM/ERP 数据源，不要声称已接入真实企业系统。
- 供应商推荐是规则排序 + LLM 解释，不是自动替企业做采购决策。
- 下单前 A2A 核验能减少上下文耦合，但最终一致性依靠数据库事务、行锁、唯一幂等键和审计日志，而不是依靠大模型。
