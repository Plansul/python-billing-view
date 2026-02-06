import streamlit as st
import pandas as pd
import plotly.express as px
from data_processor import process_uploaded_xlsx, get_cumulative_metrics

st.set_page_config(layout="wide", page_title="BI Faturamento")

st.title("📊 BI de Faturamento Acumulado")

file = st.file_uploader("Upload da Planilha Retenções 2025 .xlsx", type="xlsx")

if file:
    df_full = process_uploaded_xlsx(file)

    if df_full is not None and not df_full.empty:
        col_d, _ = st.columns([1, 3])
        with col_d:
            sel_date = st.date_input(
                "Data de Referência", value=pd.to_datetime("2026-02-06")
            )

        acc_now, acc_past, df_c, df_p, dt_p = get_cumulative_metrics(df_full, sel_date)

        diff_v = acc_now - acc_past
        diff_p = (diff_v / acc_past * 100) if acc_past > 0 else 0

        st.divider()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Faturamento Acumulado (Hoje)", f"R$ {acc_now:,.2f}")
        k2.metric(f"Mês Passado (Até {dt_p.strftime('%d/%m')})", f"R$ {acc_past:,.2f}")
        k3.metric("Diferença Bruta", f"R$ {diff_v:,.2f}", delta=f"R$ {diff_v:,.2f}")
        k4.metric("Diferença %", f"{diff_p:.2f}%", delta=f"{diff_p:.2f}%")

        st.divider()

        g1, g2 = st.columns(2)
        with g1:
            st.write("**Curva de Trajetória Acumulada**")
            d_c = df_c[df_c["DATA"].dt.day <= sel_date.day].copy()
            d_p = df_p[df_p["DATA"].dt.day <= dt_p.day].copy()
            d_c["Dia"] = d_c["DATA"].dt.day
            d_p["Dia"] = d_p["DATA"].dt.day

            plot_df = pd.concat(
                [
                    d_c[["Dia", "ACUMULADO"]].assign(Legenda="Mês Atual"),
                    d_p[["Dia", "ACUMULADO"]].assign(Legenda="Mês Anterior"),
                ]
            )
            st.plotly_chart(
                px.line(plot_df, x="Dia", y="ACUMULADO", color="Legenda", markers=True),
                use_container_width=True,
            )

        with g2:
            st.write("**Detalhamento de Emissões Diárias**")
            st.plotly_chart(
                px.bar(df_c, x="DATA", y="VALOR", title="Faturamento por Dia"),
                use_container_width=True,
            )

        with st.expander("Auditoria de Dados (Tabela Consolidada)"):
            st.dataframe(
                df_full.sort_values("DATA", ascending=False), use_container_width=True
            )
    else:
        st.error(
            "Não foi possível processar os dados das colunas 'EMISSÃO' e 'VLR BRUTO'."
        )
