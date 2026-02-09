import pandas as pd
import re


def clean_currency(x):
    if pd.isna(x) or x == "" or str(x).strip() == "-":
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace("R$", "").replace(" ", "").strip()
    try:
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except:
        return 0.0


def make_headers_unique(headers):
    seen = {}
    unique_headers = []
    for h in headers:
        h_str = str(h).strip().upper()
        if h_str in seen:
            seen[h_str] += 1
            unique_headers.append(f"{h_str}_{seen[h_str]}")
        else:
            seen[h_str] = 0
            unique_headers.append(h_str)
    return unique_headers


def process_uploaded_xlsx(uploaded_file):
    try:
        xl = pd.ExcelFile(uploaded_file)
        all_data = []
        pattern = re.compile(
            r"^(Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro)\s\d{4}$",
            re.IGNORECASE,
        )

        for sheet_name in xl.sheet_names:
            if not pattern.match(sheet_name.strip()):
                continue
            df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
            header_row_idx = None
            for i, row in df.iterrows():
                row_str = [str(val).strip().upper() for val in row.values]
                if "VLR BRUTO" in row_str and "EMISSÃO" in row_str:
                    header_row_idx = i
                    break

            if header_row_idx is not None:
                headers = make_headers_unique(df.iloc[header_row_idx].values)
                data_df = df.iloc[header_row_idx + 1 :].copy()
                data_df.columns = headers

                col_bruto = next(
                    (c for c in headers if c in ["VLR BRUTO", "VALOR BRUTO"]), None
                )
                col_prev = next(
                    (c for c in headers if c in ["PREVISÃO", "PREVISAO"]), None
                )
                col_emissao = next(
                    (c for c in headers if c in ["EMISSÃO", "EMISSAO"]), None
                )
                col_cliente = next(
                    (c for c in headers if c in ["CLIENTES", "NOME_CLIENTE"]),
                    "CLIENTES",
                )

                data_df["DIA_FAT"] = df.iloc[header_row_idx + 1 :, 1].apply(
                    lambda x: pd.to_numeric(x, errors="coerce")
                )
                data_df["VALOR_REALIZADO"] = data_df[col_bruto].apply(clean_currency)
                data_df["VALOR_PREVISAO"] = (
                    data_df[col_prev].apply(clean_currency) if col_prev else 0.0
                )
                data_df["DATA_EMISSAO"] = pd.to_datetime(
                    data_df[col_emissao], errors="coerce"
                )
                data_df["NOME_CLIENTE"] = data_df[col_cliente].astype(str).str.strip()
                data_df["SHEET_ORIGEM"] = sheet_name.strip()

                # FILTROS: Clientes sem nome, linhas de "Total" e linhas com ambos valores zerados
                data_df = data_df[
                    data_df["NOME_CLIENTE"].notna()
                    & (data_df["NOME_CLIENTE"].str.upper() != "NAN")
                    & (data_df["NOME_CLIENTE"] != "")
                    & (~data_df["NOME_CLIENTE"].str.contains("TOTAL", case=False))
                    & ~(
                        (data_df["VALOR_REALIZADO"] == 0)
                        & (data_df["VALOR_PREVISAO"] == 0)
                    )
                ]
                all_data.append(data_df)
        return pd.concat(all_data).reset_index(drop=True) if all_data else None
    except:
        return None


def get_billing_metrics(df, selected_date):
    selected_date = pd.Timestamp(selected_date).normalize()
    start_cur = selected_date.replace(day=1)
    prev_month_end = start_cur - pd.Timedelta(days=1)
    start_prev = prev_month_end.replace(day=1)
    target_prev_day = start_prev + pd.Timedelta(days=selected_date.day - 1)

    if target_prev_day.month != start_prev.month:
        target_prev_day = prev_month_end

    acc_now = df[
        (df["DATA_EMISSAO"] >= start_cur) & (df["DATA_EMISSAO"] <= selected_date)
    ]["VALOR_REALIZADO"].sum()

    acc_past = df[
        (df["DATA_EMISSAO"] >= start_prev) & (df["DATA_EMISSAO"] <= target_prev_day)
    ]["VALOR_REALIZADO"].sum()

    meta_total = df[
        (df["DATA_EMISSAO"].dt.month == start_prev.month)
        & (df["DATA_EMISSAO"].dt.year == start_prev.year)
    ]["VALOR_REALIZADO"].sum()

    df_c = (
        df[df["DATA_EMISSAO"].dt.month == selected_date.month]
        .groupby(df["DATA_EMISSAO"].dt.day)["VALOR_REALIZADO"]
        .sum()
        .cumsum()
        .reset_index()
    )
    df_c.columns = ["Dia", "ACUMULADO"]

    df_p = (
        df[df["DATA_EMISSAO"].dt.month == start_prev.month]
        .groupby(df["DATA_EMISSAO"].dt.day)["VALOR_REALIZADO"]
        .sum()
        .cumsum()
        .reset_index()
    )
    df_p.columns = ["Dia", "ACUMULADO"]

    return acc_now, acc_past, meta_total, df_c, df_p, target_prev_day
