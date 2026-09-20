from __future__ import annotations

import uuid

import requests
import streamlit as st

from .config import get_settings

settings = get_settings()

st.set_page_config(page_title="ProcureFlow", page_icon="📦", layout="wide")
st.title("📦 ProcureFlow 企业采购与供应链多智能体协同平台")
st.caption("库存核验 · 供应商询报价 · 采购订单创建 · A2A + MCP")

with st.sidebar:
    st.subheader("Agent Network")
    st.success("InventoryQueryAgent · :5005")
    st.success("SupplierQuoteAgent · :5006")
    st.success("PurchaseOrderAgent · :5007")
    confirmed = st.checkbox("我已核对并确认采购单写入", value=False)
    if "idempotency_key" not in st.session_state:
        st.session_state.idempotency_key = f"web-{uuid.uuid4()}"
    if st.button("生成新的幂等键"):
        st.session_state.idempotency_key = f"web-{uuid.uuid4()}"
    st.code(st.session_state.idempotency_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("例如：查询 MAT-1001 库存，并比较采购 100 件的供应商报价"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            response = requests.post(
                f"{settings.api_url}/api/chat",
                json={
                    "query": prompt,
                    "confirmed": confirmed,
                    "idempotency_key": st.session_state.idempotency_key,
                },
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            answer = data["answer"]
            st.markdown(answer)
            with st.expander("查看 Agent 原始结果"):
                st.json(data["results"])
        except Exception as exc:
            answer = f"请求失败：{exc}"
            st.error(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

