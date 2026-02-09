import streamlit as st
import pandas as pd
import plotly.express as px
from data_processor import process_uploaded_xlsx, get_billing_metrics

st.set_page_config(layout="wide", page_title="BI Faturamento")

# --- CSS Customizado para aproximar do visual dos prints ---
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { font-size: 22px; }
    .main { background-color: #f8f9fa; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("⚙️ Controles")
    file = st.file_uploader("Upload Planilha Retenções", type="xlsx")
    sel_date = st.date_input("Data de Referência", value=pd.to_datetime("2026-02-09"))

if file:
    df_raw = process_uploaded_xlsx(file)

    if df_raw is not None and not df_raw.empty:
        acc_now, acc_past, meta_total, df_c, df_p, dt_p = get_billing_metrics(
            df_raw, sel_date
        )

        # --- LINHA 1: 4 INSIGHTS CARDS ---
        st.markdown("### 📊 Performance Diária Acumulada")
        diff_val = acc_now - acc_past
        perc_diff = (diff_val / acc_past * 100) if acc_past > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Acumulado Mês Atual", f"R$ {acc_now:,.2f}")
        with c2:
            st.metric("Acumulado Mês Anterior", f"R$ {acc_past:,.2f}")
        with c3:
            st.metric(
                "Diferença Valor Bruto",
                f"R$ {diff_val:,.2f}",
                delta=f"R$ {diff_val:,.2f}",
            )
        with c4:
            st.metric("Diferença %", f"{perc_diff:.2f}%", delta=f"{perc_diff:.2f}%")

        st.divider()

        # --- LINHA 2: METAS E ALERTAS ---
        st.markdown("### 🎯 Metas e Saúde do Mês")

        # Lógica de Atrasados
        meses_nomes = [
            "Janeiro",
            "Fevereiro",
            "Março",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ]
        sheet_ref = f"{meses_nomes[sel_date.month-1]} {sel_date.year}"
        df_mes_atual = df_raw[
            df_raw["SHEET_ORIGEM"].str.upper() == sheet_ref.upper()
        ].copy()

        atrasados_count = 0
        if not df_mes_atual.empty:
            atrasados_count = len(
                df_mes_atual[
                    (df_mes_atual["VALOR_REALIZADO"] <= 0)
                    & (df_mes_atual["DIA_FAT"] < sel_date.day)
                ]
            )

        progresso_pct = (acc_now / meta_total * 100) if meta_total > 0 else 0

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Alvo de Faturamento (Total Mês Ant.)", f"R$ {meta_total:,.2f}")
        with m2:
            st.metric("% Concluído da Meta", f"{progresso_pct:.1f}%")
        with m3:
            st.metric(
                "Clientes em Atraso Crítico",
                f"{atrasados_count}",
                delta="Ação Necessária",
                delta_color="inverse",
            )

        st.divider()

        # --- LINHA 3: GRÁFICO (ESQUERDA) E TABELA (DIREITA) ---
        col_esq, col_dir = st.columns([1.2, 0.8])

        with col_esq:
            st.write("**📈 Trajetória de Faturamento Acumulado**")
            # Switch de Visualização
            tipo_grafico = st.toggle("Ver em Área", value=False)

            d_c = df_c[df_c["DATA_EMISSAO"].dt.day <= sel_date.day].copy()
            d_p = df_p[df_p["DATA_EMISSAO"].dt.day <= dt_p.day].copy()
            d_c["Dia"] = d_c["DATA_EMISSAO"].dt.day
            d_p["Dia"] = d_p["DATA_EMISSAO"].dt.day
            plot_df = pd.concat(
                [
                    d_c[["Dia", "ACUMULADO"]].assign(Legenda="Mês Atual"),
                    d_p[["Dia", "ACUMULADO"]].assign(Legenda="Mês Anterior"),
                ]
            )

            fig = (
                px.area(plot_df, x="Dia", y="ACUMULADO", color="Legenda")
                if tipo_grafico
                else px.line(
                    plot_df, x="Dia", y="ACUMULADO", color="Legenda", markers=True
                )
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_dir:
            st.write("**📋 Detalhamento de Clientes (Status)**")

            def check_status(row, day):
                if row["VALOR_REALIZADO"] > 0:
                    return "✅ Concluído"
                if pd.isna(row["DIA_FAT"]):
                    return "⚪ S/ Janela"
                return "🚨 Atrasado" if row["DIA_FAT"] < day else "⏳ No Prazo"

            df_mes_atual["STATUS"] = df_mes_atual.apply(
                lambda r: check_status(r, sel_date.day), axis=1
            )

            st.dataframe(
                df_mes_atual[
                    [
                        "DIA_FAT",
                        "NOME_CLIENTE",
                        "VALOR_PREVISAO",
                        "VALOR_REALIZADO",
                        "STATUS",
                    ]
                ]
                .sort_values(["DIA_FAT", "STATUS"])
                .style.applymap(
                    lambda x: (
                        "color: red; font-weight: bold"
                        if x == "🚨 Atrasado"
                        else ("color: green" if x == "✅ Concluído" else "")
                    ),
                    subset=["STATUS"],
                ),
                use_container_width=True,
                height=450,
            )

    else:
        st.info("Aguardando upload da planilha e processamento dos dados...")
