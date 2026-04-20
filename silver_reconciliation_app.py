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
    /* ── Base ───────────────────────────────────────────────────── */
    .stApp, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0A0A0A !important;
        color: #D8D8D8 !important;
    }
    p, li { color: #D8D8D8; }
    .stMarkdown p { color: #D8D8D8 !important; }

    /* ── Top chrome ─────────────────────────────────────────────── */
    [data-testid="stHeader"] {
        background: #0A0A0A !important;
        border-bottom: 1px solid #1A1A1A;
        box-shadow: none;
    }
    [data-testid="stToolbar"] button svg { fill: #555 !important; }
    [data-testid="stDecoration"] { display: none; }

    /* ── Hero strip ─────────────────────────────────────────────── */
    .hero-wrap {
        display: flex;
        align-items: center;
        gap: 18px;
        padding: 20px 24px;
        background: #111111;
        border: 1px solid #1E1E1E;
        border-left: 4px solid #CC4400;
        border-radius: 10px;
        margin-bottom: 28px;
    }
    .hero-wrap img { border-radius: 6px; flex-shrink: 0; }
    .hero-title {
        margin: 0;
        font-size: 1.55rem;
        font-weight: 700;
        color: #F2F2F2;
        letter-spacing: -0.3px;
        line-height: 1.2;
    }
    .hero-tag {
        margin: 4px 0 0 0;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #CC4400;
    }

    /* ── Pill tabs ──────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: none !important;
        gap: 8px;
        padding: 0;
        margin-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #111111 !important;
        border: 1px solid #252525 !important;
        border-radius: 30px !important;
        color: #555 !important;
        font-weight: 700 !important;
        font-size: 0.8rem !important;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        padding: 8px 30px !important;
        transition: all 0.18s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        border-color: #CC4400 !important;
        color: #CC4400 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #CC4400 !important;
        border-color: #CC4400 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(204,68,0,0.35) !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: #111111 !important;
        border: 1px solid #1E1E1E !important;
        border-radius: 12px !important;
        padding: 28px 28px 24px !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5) !important;
    }

    /* ── Section labels ─────────────────────────────────────────── */
    h2, h3 {
        color: #E0E0E0 !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.4px !important;
        border: none !important;
        border-left: 3px solid #CC4400 !important;
        padding: 2px 0 2px 10px !important;
        margin-bottom: 20px !important;
    }

    /* ── Upload cards ───────────────────────────────────────────── */
    [data-testid="stFileUploader"] {
        background: #0D0D0D;
        border: 1px solid #222222;
        border-radius: 10px;
        padding: 10px 14px;
        transition: all 0.2s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #CC4400;
        box-shadow: 0 0 0 1px #CC4400, 0 0 18px rgba(204,68,0,0.12);
    }
    [data-testid="stFileUploader"] label {
        font-weight: 700 !important;
        color: #888888 !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
        border: none !important;
    }
    [data-testid="stFileUploaderDropzone"] span { color: #444 !important; }

    /* ── Download / action buttons ──────────────────────────────── */
    .stDownloadButton > button, .stButton > button {
        background: transparent !important;
        color: #CC4400 !important;
        border: 1.5px solid #CC4400 !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
        padding: 8px 24px !important;
        transition: all 0.18s ease !important;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {
        background: #CC4400 !important;
        color: white !important;
        box-shadow: 0 0 16px rgba(204,68,0,0.3) !important;
    }

    /* ── Alerts ─────────────────────────────────────────────────── */
    [data-testid="stAlert"] {
        background: #0F0F0F !important;
        border: 1px solid #1E1E1E !important;
        border-left: 3px solid #CC4400 !important;
        border-radius: 8px !important;
        color: #AAAAAA !important;
    }
    .stAlert { background: #0F0F0F !important; color: #AAAAAA !important; }

    /* ── Dataframe ──────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {
        background: #0D0D0D !important;
        color: #D8D8D8 !important;
        border: 1px solid #1E1E1E !important;
        border-radius: 8px !important;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] thead th {
        background: #CC4400 !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
    }
    [data-testid="stDataFrame"] tbody tr:nth-child(even) td {
        background: #131313 !important;
    }

    /* ── Footer ─────────────────────────────────────────────────── */
    .footer-credit {
        text-align: center;
        color: #333333;
        font-size: 0.72rem;
        letter-spacing: 0.5px;
        margin-top: 36px;
        padding-top: 14px;
        border-top: 1px solid #181818;
    }
</style>
""", unsafe_allow_html=True)

_logo_b64 = __import__('base64').b64encode(open("TPM_Logo.png", "rb").read()).decode()
st.markdown(f"""
<div class="hero-wrap">
    <img src="data:image/png;base64,{_logo_b64}" width="72"/>
    <div>
        <p class="hero-title">Ledger Reconciliation</p>
        <p class="hero-tag">Texas Precious Metals</p>
    </div>
</div>
""", unsafe_allow_html=True)

tab_silver, tab_gold = st.tabs(["Silver", "Gold"])

# ── Silver ──────────────────────────────────────────────────────────────────
with tab_silver:
    st.subheader("Silver Reconciliation")
    col1, col2 = st.columns(2)
    with col1:
        silver_ledger_file = st.file_uploader("Ledger", type=["xlsx", "csv"],
                                              key="silver_ledger")
    with col2:
        silver_credit_file = st.file_uploader("Data View", type=["xlsx", "csv"],
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
        gold_credit_file = st.file_uploader("Data View", type=["xlsx", "csv"],
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

st.markdown('<div class="footer-credit">Made by Michael Ginsberg</div>', unsafe_allow_html=True)
