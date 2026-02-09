import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_processor import process_uploaded_xlsx, get_billing_metrics

st.set_page_config(layout="wide", page_title="BI Faturamento", page_icon="📈")


# Função auxiliar para formatar moeda no padrão BR
def format_br(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


with st.sidebar:
    st.header("⚙️ Configurações")
    file = st.file_uploader("Upload Planilha Retenções", type="xlsx")
    sel_date = st.date_input("Data de Referência", value=pd.to_datetime("2026-02-09"))

if file:
    df_raw = process_uploaded_xlsx(file)

    if df_raw is not None and not df_raw.empty:
        # Atualiza opções do filtro com dados da planilha
        clientes_lista = sorted(df_raw["NOME_CLIENTE"].unique())
        f_clientes = st.sidebar.multiselect(
            "Filtrar Clientes", options=clientes_lista, key="filtro_cli"
        )

        # Aplica o filtro de clientes se houver seleção
        df_filtered = df_raw.copy()
        if f_clientes:
            df_filtered = df_filtered[df_filtered["NOME_CLIENTE"].isin(f_clientes)]

        acc_now, acc_past, meta_total, df_c, df_p, dt_p = get_billing_metrics(
            df_filtered, sel_date
        )

        # --- LINHA 1: 4 CARDS ACUMULATIVOS ---
        st.subheader(f"📅 Desempenho Acumulado (até dia {sel_date.day})")
        diff_val = acc_now - acc_past
        perc_diff = (diff_val / acc_past * 100) if acc_past > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Acumulado Mês Atual", format_br(acc_now))
        c2.metric("Acumulado Mês Anterior", format_br(acc_past))
        c3.metric("Diferença Valor", format_br(diff_val), delta=format_br(diff_val))
        c4.metric("Diferença %", f"{perc_diff:.2f}%", delta=f"{perc_diff:.2f}%")

        st.divider()

        # --- LINHA 2: METAS E SAÚDE ---
        st.subheader("🎯 Metas e Alertas Operacionais")

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

        # Filtra para a aba do mês atual selecionado
        df_mes_atual = df_filtered[
            df_filtered["SHEET_ORIGEM"].str.upper() == sheet_ref.upper()
        ].copy()

        def check_status(row, day):
            if row["VALOR_REALIZADO"] > 0:
                return "✅ Concluído"
            if pd.isna(row["DIA_FAT"]):
                return "⚪ S/ Janela"
            return "🚨 Atrasado" if row["DIA_FAT"] < day else "⏳ No Prazo"

        df_mes_atual["STATUS"] = df_mes_atual.apply(
            lambda r: check_status(r, sel_date.day), axis=1
        )
        df_operacional = df_mes_atual[df_mes_atual["STATUS"] != "⚪ S/ Janela"].copy()

        atrasados_count = len(df_operacional[df_operacional["STATUS"] == "🚨 Atrasado"])
        progresso_pct = (acc_now / meta_total * 100) if meta_total > 0 else 0

        m1, m2, m3 = st.columns(3)

        with m1:
            st.metric("Alvo (Total Mês Ant.)", format_br(meta_total))
            st.write(f"**Progresso: {progresso_pct:.1f}%**")
            st.progress(min(progresso_pct / 100, 1.0))

        with m2:
            st.metric("% Atingido da Meta", f"{progresso_pct:.1f}%")
            fig_pizza = go.Figure(
                data=[
                    go.Pie(
                        values=[acc_now, max(0, meta_total - acc_now)],
                        labels=["Realizado", "Falta"],
                        hole=0.7,
                        marker_colors=["#2E7D32", "#e0e0e0"],
                        textinfo="none",
                    )
                ]
            )
            fig_pizza.update_layout(
                showlegend=False,
                margin=dict(t=0, b=0, l=0, r=0),
                height=80,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            # AJUSTE 1: replace use_container_width with width='stretch'
            st.plotly_chart(
                fig_pizza, width="stretch", config={"displayModeBar": False}
            )

        with m3:
            st.metric(
                "Atrasos Críticos",
                f"{atrasados_count}",
                delta="Faturamentos Atrasados",
                delta_color="inverse",
            )

        st.divider()

        # --- LINHA 3: GRÁFICO E TABELA ---
        col_grafico, col_tabela = st.columns([1.2, 0.8])

        with col_grafico:
            st.write("**📈 Trajetória de Faturamento Acumulado**")
            d_c = df_c[df_c["Dia"] <= sel_date.day].copy()
            d_p = df_p[df_p["Dia"] <= sel_date.day].copy()

            plot_df = pd.concat(
                [
                    d_c.assign(Legenda="Mês Atual"),
                    d_p.assign(Legenda="Mês Anterior"),
                ]
            )
            fig = px.line(
                plot_df,
                x="Dia",
                y="ACUMULADO",
                color="Legenda",
                markers=True,
                color_discrete_map={"Mês Atual": "#0047AB", "Mês Anterior": "#BDC3C7"},
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=20, b=0),
                legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
            )
            # AJUSTE 1: replace use_container_width with width='stretch'
            st.plotly_chart(fig, width="stretch")

        with col_tabela:
            st.write("**📋 Clientes (Ordenado por Valor)**")
            # Ordenação por Valor Realizado Crescente
            df_tabela_final = df_operacional[
                [
                    "DIA_FAT",
                    "NOME_CLIENTE",
                    "VALOR_PREVISAO",
                    "VALOR_REALIZADO",
                    "STATUS",
                ]
            ].sort_values(by="VALOR_REALIZADO", ascending=True)

            # AJUSTE 3: Formatação do DIA_FAT para inteiro
            st.dataframe(
                df_tabela_final.style.format(
                    {
                        "DIA_FAT": "{:.0f}",
                        "VALOR_PREVISAO": format_br,
                        "VALOR_REALIZADO": format_br,
                    }
                ).map(
                    lambda x: (
                        "color: #D32F2F; font-weight: bold"
                        if x == "🚨 Atrasado"
                        else ("color: #2E7D32" if x == "✅ Concluído" else "")
                    ),
                    subset=["STATUS"],
                ),
                width="stretch",  # AJUSTE 1: replace use_container_width with width='stretch'
                height=400,
                hide_index=True,
            )
    else:
        st.info("Aguardando upload.")
