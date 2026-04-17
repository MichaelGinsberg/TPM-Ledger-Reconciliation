import streamlit as st
import pandas as pd
from io import BytesIO

UNNAMED_DROP = [
    'Unnamed: 0', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4',
    'Unnamed: 5', 'Unnamed: 7', 'Unnamed: 8', 'Unnamed: 9', 'Unnamed: 10',
    'Unnamed: 11', 'Unnamed: 13', 'Unnamed: 14', 'Unnamed: 16', 'Unnamed: 15',
    'Unnamed: 17', 'Unnamed: 18', 'Unnamed: 19', 'Unnamed: 20', 'Unnamed: 21',
    'Unnamed: 22', 'Unnamed: 23', 'Unnamed: 24', 'Unnamed: 25', 'Unnamed: 26',
    'Unnamed: 27', 'Unnamed: 29', 'Unnamed: 28', 'Unnamed: 30', 'Unnamed: 31',
    'Unnamed: 32', 'Unnamed: 33', 'Unnamed: 34', 'Unnamed: 35', 'Unnamed: 36',
    'Unnamed: 37', 'Unnamed: 38', 'Unnamed: 39', 'Unnamed: 40', 'Unnamed: 41',
    'Unnamed: 42', 'Unnamed: 43', 'Unnamed: 44', 'Unnamed: 45', 'Unnamed: 46',
    'Unnamed: 47', 'Unnamed: 48', 'Unnamed: 50', 'Unnamed: 51', 'Unnamed: 52',
    'Unnamed: 53', 'Unnamed: 54', 'Unnamed: 55', 'Unnamed: 57', 'Unnamed: 58',
    'Unnamed: 59', 'Unnamed: 60', 'Unnamed: 61', 'Unnamed: 62', 'Unnamed: 63',
    'Unnamed: 64', 'Unnamed: 65', 'Unnamed: 66', 'Unnamed: 68', 'Unnamed: 67',
    'Unnamed: 69', 'Unnamed: 71', 'Unnamed: 70',
]


st.set_page_config(page_title="TPM Ledger Reconciliation", page_icon="Tab_Logo.png")


def _to_numeric(series):
    return pd.to_numeric(series.astype(str).str.replace(',', '', regex=False), errors='coerce')


def clean_silver(df):
    df = df.drop(columns=UNNAMED_DROP)
    df = df.drop(df.index[:10])
    df = df.rename(columns={
        'Unnamed: 6': 'Date',
        'Unnamed: 12': 'Order #',
        'Unnamed: 49': 'Silver Debit',
        'Unnamed: 56': 'Credit',
    })
    df['Credit'] = -_to_numeric(df['Credit']).abs()
    df['Silver Debit'] = _to_numeric(df['Silver Debit'])
    df['Credit'] = df['Credit'].replace(-0, 0)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%m/%d/%Y')
    return df


def clean_gold(df):
    df = df.drop(columns=UNNAMED_DROP)
    df = df.drop(df.index[:10])
    df = df.rename(columns={
        'Unnamed: 6': 'Date',
        'Unnamed: 12': 'Order #',
        'Unnamed: 49': 'Gold Debit',
        'Unnamed: 56': 'Credit',
    })
    df['Credit'] = -_to_numeric(df['Credit']).abs()
    df['Gold Debit'] = _to_numeric(df['Gold Debit'])
    df['Credit'] = df['Credit'].replace(-0, 0)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%m/%d/%Y')
    return df


def clean_inv(df):
    df = df.drop(columns=['SITE', 'FROM SITE', 'ACCOUNT', 'UC1', 'UC2', 'UC3', 'UC4',
                          'JOURNAL', 'Item', 'C/V NUM', 'Name'])
    df = df.rename(columns={'Document Number': 'Order #', 'DATE': 'Date', 'AMOUNT': 'Credit'})
    df['Date'] = df['Date'].dt.strftime('%m/%d/%Y')
    df = df.drop(columns=['REFERENCE'])
    df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce')
    return df


def build_lookup(df_inv):
    return (
        df_inv
        .dropna(subset=['Order #'])
        .drop_duplicates(subset=['Date', 'Credit'])
        .set_index(['Date', 'Credit'])['Order #']
        .to_dict()
    )


def match_orders(df, debit_col, inv_lookup):
    df['Order #'] = [
        inv_lookup.get((date, credit), inv_lookup.get((date, debit), orig))
        for date, credit, debit, orig in zip(
            df['Date'], df['Credit'], df[debit_col], df['Order #']
        )
    ]
    return df


def group_results(df, debit_col):
    out = df.groupby('Order #', as_index=False)[[debit_col, 'Credit']].sum()
    out[debit_col] = out[debit_col].round(2)
    out['Credit'] = out['Credit'].round(2)
    out['Remainder'] = out[debit_col] + out['Credit']
    return out


def read_file(f):
    """Read an uploaded file as a DataFrame regardless of whether it is csv or xlsx."""
    name = f.name.lower()
    if name.endswith('.csv'):
        return pd.read_csv(f)
    return pd.read_excel(f)


def to_excel_bytes(df):
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


# --- UI ---

st.markdown("""
<style>
    /* Orange accent on tab active state */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #CC4400 !important;
        border-bottom-color: #CC4400 !important;
    }
    /* Orange accent on buttons */
    .stDownloadButton > button, .stButton > button {
        background-color: #CC4400 !important;
        color: white !important;
        border: none !important;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {
        background-color: #AA3300 !important;
    }
    /* Orange subheader underline accent */
    h2, h3 {
        border-bottom: 2px solid #CC4400;
        padding-bottom: 4px;
    }
    /* Logo positioning */
    [data-testid="stHeader"] {
        background-color: transparent;
    }
    /* Push main content away from left edge so logo doesn't overlap */
    .logo-corner {
        position: fixed;
        top: 8px;
        left: 10px;
        z-index: 9999;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="logo-corner">
    <img src="data:image/png;base64,{logo_b64}" width="160" style="display:block; margin:0 auto;"/>
    <p style="font-size:14px; color:gray; margin-top:6px;">Made by Michael Ginsberg</p>
</div>
""".replace("{logo_b64}", __import__('base64').b64encode(open("TPM_Logo.png", "rb").read()).decode()), unsafe_allow_html=True)

st.title("Ledger Reconciliation")

tab_silver, tab_gold = st.tabs(["Silver", "Gold"])

# ── Silver ──────────────────────────────────────────────────────────────────
with tab_silver:
    st.subheader("Silver Reconciliation")
    col1, col2 = st.columns(2)
    with col1:
        silver_ledger_file = st.file_uploader("Ledger", type=["xlsx", "csv"],
                                              key="silver_ledger")
    with col2:
        silver_credit_file = st.file_uploader("Credit", type=["xlsx", "csv"],
                                              key="silver_credit")

    if silver_ledger_file and silver_credit_file:
        try:
            df_silver = clean_silver(read_file(silver_ledger_file))
            df_inv_s = clean_inv(read_file(silver_credit_file))
            df_silver = match_orders(df_silver, 'Silver Debit', build_lookup(df_inv_s))
            result_s = group_results(df_silver, 'Silver Debit')

            st.success(f"Processed {len(result_s)} order(s).")
            st.dataframe(result_s, use_container_width=True)
            st.download_button(
                label="Download Result",
                data=to_excel_bytes(result_s),
                file_name="silver_reconciliation.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_silver",
            )
        except Exception as e:
            st.error(f"Error during processing: {e}")
    elif silver_ledger_file or silver_credit_file:
        st.info("Upload both files to run the reconciliation.")

# ── Gold ─────────────────────────────────────────────────────────────────────
with tab_gold:
    st.subheader("Gold Reconciliation")
    col3, col4 = st.columns(2)
    with col3:
        gold_ledger_file = st.file_uploader("Ledger", type=["xlsx", "csv"],
                                            key="gold_ledger")
    with col4:
        gold_credit_file = st.file_uploader("Credit", type=["xlsx", "csv"],
                                            key="gold_credit")

    if gold_ledger_file and gold_credit_file:
        try:
            df_gold = clean_gold(read_file(gold_ledger_file))
            df_inv_g = clean_inv(read_file(gold_credit_file))
            df_gold = match_orders(df_gold, 'Gold Debit', build_lookup(df_inv_g))
            result_g = group_results(df_gold, 'Gold Debit')

            st.success(f"Processed {len(result_g)} order(s).")
            st.dataframe(result_g, use_container_width=True)
            st.download_button(
                label="Download Result",
                data=to_excel_bytes(result_g),
                file_name="gold_reconciliation.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_gold",
            )
        except Exception as e:
            st.error(f"Error during processing: {e}")
    elif gold_ledger_file or gold_credit_file:
        st.info("Upload both files to run the reconciliation.")
