import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Rapha Ads Intelligence", layout="wide")

# --------------------------------------------------
# LOGO + HEADER (SAFE)
# --------------------------------------------------
col1, col2 = st.columns([1, 6])

with col1:
    try:
        st.image("Logo.png", width=110)
    except:
        pass

with col2:
    st.markdown("## Rapha Ads Intelligence")

# --------------------------------------------------
# STYLING
# --------------------------------------------------
st.markdown("""
<style>
.exec-card {
    background: #f8fafc;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
    border: 1px solid #e2e8f0;
}
.section-title {
    font-size: 18px;
    font-weight: 600;
}
.muted {
    color: #64748b;
}
.highlight {
    background: #013a7a;
    color: white;
    padding: 15px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("Rapha | Google Ads Product Intelligence Dashboard")

# --------------------------------------------------
# LOAD DATA (SAFE)
# --------------------------------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("rapha_campaign_clean.csv")
    except:
        st.error("Missing CSV file")
        st.stop()

    num_cols = ["cost","clicks","impr","conversions","conv_value"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    currency = "GBP"
    if "currency_code" in df.columns and not df.empty:
        currency = df["currency_code"].iloc[0]

    symbol_map = {"GBP": "£", "EUR": "€", "USD": "$"}
    currency_symbol = symbol_map.get(currency, "£")

    return df, currency_symbol

df, currency_symbol = load_data()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
campaign_filter = st.sidebar.multiselect(
    "Select Campaigns",
    options=sorted(df["campaign"].dropna().unique()),
    default=list(df["campaign"].dropna().unique())
)

filtered = df[df["campaign"].isin(campaign_filter)]

if filtered.empty:
    st.warning("No data selected")
    st.stop()

# --------------------------------------------------
# PRODUCT PERF
# --------------------------------------------------
product_perf = (
    filtered.groupby("product_title")
    .agg(
        Spend=("cost","sum"),
        Revenue=("conv_value","sum"),
        Conversions=("conversions","sum")
    )
    .reset_index()
)

product_perf["ROAS"] = product_perf["Revenue"] / product_perf["Spend"].replace(0, np.nan)
product_perf = product_perf.fillna(0)

# --------------------------------------------------
# GLOBAL METRICS
# --------------------------------------------------
total_spend = filtered["cost"].sum()
total_rev = filtered["conv_value"].sum()
total_conv = filtered["conversions"].sum()
roas = total_rev / total_spend if total_spend != 0 else 0

# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Overview",
    "Performance Snapshot",
    "Products",
    "Campaigns",
    "Budget Engine",
    "Spend Analysis",
    "Spend Simulator"
])

# --------------------------------------------------
# TAB 1 — OVERVIEW (UNCHANGED)
# --------------------------------------------------
with tab1:
    st.markdown("## 🧠 Executive Overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Revenue", f"{currency_symbol}{total_rev:,.0f}")
    c2.metric("💸 Spend", f"{currency_symbol}{total_spend:,.0f}")
    c3.metric("📈 ROAS", f"{roas:.2f}")

# --------------------------------------------------
# TAB 2 — SNAPSHOT (SAFE LINE)
# --------------------------------------------------
with tab2:

    scatter_df = (
        filtered.groupby("product_title")
        .agg(Spend=("cost","sum"), Revenue=("conv_value","sum"))
        .reset_index()
    )

    fig = px.scatter(
        scatter_df,
        x="Spend",
        y="Revenue",
        hover_name="product_title",
        size="Revenue",
        size_max=25
    )

    if not scatter_df.empty and total_spend > 0:
        fig.add_shape(
            type="line",
            x0=scatter_df["Spend"].min(),
            y0=scatter_df["Spend"].min() * roas,
            x1=scatter_df["Spend"].max(),
            y1=scatter_df["Spend"].max() * roas,
            line=dict(dash="dot")
        )

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TAB 3 — PRODUCTS (UNCHANGED)
# --------------------------------------------------
with tab3:
    selected_products = st.multiselect(
        "Select Products",
        options=sorted(product_perf["product_title"].dropna().unique()),
        default=[]
    )

    filtered_products = product_perf.copy()

    if selected_products:
        filtered_products = filtered_products[
            filtered_products["product_title"].isin(selected_products)
        ]

    st.dataframe(filtered_products, use_container_width=True)

# --------------------------------------------------
# TAB 4 — CAMPAIGNS (UNCHANGED)
# --------------------------------------------------
with tab4:
    campaign_perf = (
        filtered.groupby("campaign")
        .agg(Spend=("cost", "sum"), Revenue=("conv_value", "sum"))
        .reset_index()
    )

    campaign_perf["ROAS"] = campaign_perf["Revenue"] / campaign_perf["Spend"].replace(0, np.nan)
    campaign_perf = campaign_perf.fillna(0)

    st.dataframe(campaign_perf, use_container_width=True)

# --------------------------------------------------
# TAB 5 — BUDGET ENGINE (UNCHANGED)
# --------------------------------------------------
with tab5:
    df_budget = product_perf.copy()

    avg_conv = df_budget["Conversions"].mean()
    avg_spend = df_budget["Spend"].mean()

    def rec(row):
        if row["Conversions"] > avg_conv * 1.3 and row["Spend"] > avg_spend:
            return "🟢 Scale"
        elif row["Conversions"] < avg_conv * 0.7:
            return "🔴 Cut"
        else:
            return "🟡 Hold"

    df_budget["Action"] = df_budget.apply(rec, axis=1)

    st.dataframe(df_budget, use_container_width=True)

# --------------------------------------------------
# TAB 6 — CURVES (SAFE)
# --------------------------------------------------
with tab6:

    selected_campaigns = st.multiselect(
        "Select up to 2 campaigns",
        options=filtered["campaign"].unique(),
        default=list(filtered["campaign"].unique())[:2]
    )

    channel_df = (
        filtered[filtered["campaign"].isin(selected_campaigns)]
        .groupby("campaign")
        .agg(Spend=("cost","sum"), Revenue=("conv_value","sum"))
        .reset_index()
    )

    curves = []

    for _, row in channel_df.iterrows():
        spend = max(row["Spend"],1)
        revenue = max(row["Revenue"],1)

        x = np.linspace(0, spend*2,100)
        y = revenue*(1-np.exp(-x/spend))

        curves.append(pd.DataFrame({
            "Spend":x,
            "Revenue":y,
            "Channel":row["campaign"]
        }))

    if curves:
        curve_df = pd.concat(curves)
        fig = px.line(curve_df, x="Spend", y="Revenue", color="Channel")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough data")

# --------------------------------------------------
# TAB 7 — SIMULATOR (CRASH FIXED ONLY)
# --------------------------------------------------
with tab7:

    campaign = st.selectbox("Select Campaign", filtered["campaign"].unique())

    data = filtered[filtered["campaign"] == campaign]

    spend = data["cost"].sum()
    revenue = data["conv_value"].sum()

    if spend == 0:
        st.warning("No data available")
    else:

        pct = st.slider("Increase Spend (%)", 0, 100, 20)

        new_spend = spend * (1 + pct / 100)

        def curve(x):
            return revenue * (1 - np.exp(-x / spend))

        current = curve(spend)
        new = curve(new_spend)

        delta_pct = ((new - current)/current)*100 if current != 0 else 0

        st.metric(
            "Incremental Revenue",
            f"{currency_symbol}{(new - current):,.0f}",
            delta=f"{delta_pct:.1f}%"
        )