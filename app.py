import streamlit as st
import pandas as pd
import plotly.express as px
from data_processor import process_uploaded_xlsx, get_billing_metrics

st.set_page_config(layout="wide", page_title="BI Faturamento")

st.title("📊 BI de Faturamento Proativo")

file = st.file_uploader("Upload da Planilha Retenções", type="xlsx")

if file:
    df_raw = process_uploaded_xlsx(file)

    if df_raw is not None and not df_raw.empty:
        col_input, _ = st.columns([1, 3])
        with col_input:
            sel_date = st.date_input(
                "Data de Referência", value=pd.to_datetime("2026-02-09")
            )

        # d_now e d_past aqui representam o ACUMULADO MTD (Day 1 até Hoje)
        acc_now, acc_past, meta_total, qtd_atrasados, df_c, df_p, dt_p = (
            get_billing_metrics(df_raw, sel_date)
        )

        # --- LINHA 1: 4 CARDS PRINCIPAIS (ACUMULADOS) ---
        diff_val = acc_now - acc_past
        perc_diff = (diff_val / acc_past * 100) if acc_past > 0 else 0

        st.markdown(
            f"#### 📅 Performance Acumulada: 01/{sel_date.month:02d} até {sel_date.day:02d}/{sel_date.month:02d}"
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Acumulado Mês Atual", f"R$ {acc_now:,.2f}")
        c2.metric("Acumulado Mês Anterior", f"R$ {acc_past:,.2f}")
        c3.metric(
            "Diferença Valor Bruto", f"R$ {diff_val:,.2f}", delta=f"R$ {diff_val:,.2f}"
        )
        c4.metric("Diferença %", f"{perc_diff:.2f}%", delta=f"{perc_diff:.2f}%")

        st.divider()

        # Próximos passos: Implementar os 3 cards inferiores, o switch de gráfico e a tabela lateral.
        # ...
