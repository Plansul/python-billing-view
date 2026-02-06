import pandas as pd


def clean_currency(x):
    if pd.isna(x) or x == "":
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


def process_uploaded_xlsx(uploaded_file):
    try:
        xl = pd.ExcelFile(uploaded_file)
        all_data = []
        for sheet_name in xl.sheet_names:
            if not any(char.isdigit() for char in sheet_name):
                continue
            if any(w in sheet_name.upper() for w in ["PENDÊNCIAS", "INADIMPLENTES"]):
                continue

            df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
            header_row = None
            for i, row in df.iterrows():
                row_vals = [str(v).strip().upper() for v in row.values]
                if "EMISSÃO" in row_vals and "VLR BRUTO" in row_vals:
                    header_row = i
                    break

            if header_row is not None:
                df_final = df.iloc[header_row + 1 :].copy()
                df_final.columns = [
                    str(c).strip().upper() for c in df.iloc[header_row].values
                ]
                df_final["VALOR"] = df_final["VLR BRUTO"].apply(clean_currency)
                df_final["DATA"] = pd.to_datetime(df_final["EMISSÃO"], errors="coerce")

                clean_df = df_final.dropna(subset=["DATA", "VALOR"])
                clean_df = clean_df[clean_df["VALOR"] > 0]
                all_data.append(clean_df[["DATA", "VALOR"]])

        if not all_data:
            return None
        return (
            pd.concat(all_data)
            .groupby("DATA")["VALOR"]
            .sum()
            .reset_index()
            .sort_values("DATA")
        )
    except:
        return None


def get_cumulative_metrics(df, selected_date):
    selected_date = pd.Timestamp(selected_date).normalize()
    start_cur = selected_date.replace(day=1)
    prev_month_end = start_cur - pd.Timedelta(days=1)
    start_prev = prev_month_end.replace(day=1)

    target_prev_day = start_prev + pd.Timedelta(days=selected_date.day - 1)
    if target_prev_day.month != start_prev.month:
        target_prev_day = prev_month_end

    acc_now = df[(df["DATA"] >= start_cur) & (df["DATA"] <= selected_date)][
        "VALOR"
    ].sum()
    acc_past = df[(df["DATA"] >= start_prev) & (df["DATA"] <= target_prev_day)][
        "VALOR"
    ].sum()

    df_c = df[df["DATA"].dt.month == selected_date.month].copy().sort_values("DATA")
    df_p = df[df["DATA"].dt.month == start_prev.month].copy().sort_values("DATA")

    df_c["ACUMULADO"] = df_c["VALOR"].cumsum()
    df_p["ACUMULADO"] = df_p["VALOR"].cumsum()

    return acc_now, acc_past, df_c, df_p, target_prev_day
