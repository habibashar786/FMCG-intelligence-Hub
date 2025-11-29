import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

st.set_page_config(page_title="Reports", page_icon="chart", layout="wide")

st.title("FMCG Sales Reports")
st.markdown("Visual insights from your data")

data_file = Path(__file__).parent.parent.parent / "data" / "sample_fmcg_data.csv"

if data_file.exists():
    df = pd.read_csv(data_file)
    df['date'] = pd.to_datetime(df['date'])
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_revenue = df['total_price'].sum()
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    
    with col2:
        total_transactions = len(df)
        st.metric("Total Transactions", f"{total_transactions:,}")
    
    with col3:
        unique_customers = df['customer_id'].nunique()
        st.metric("Unique Customers", f"{unique_customers:,}")
    
    with col4:
        avg_transaction = df['total_price'].mean()
        st.metric("Avg Transaction", f"${avg_transaction:.2f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sales by Category")
        category_sales = df.groupby('category')['total_price'].sum().sort_values(ascending=True)
        fig = px.bar(
            x=category_sales.values,
            y=category_sales.index,
            orientation='h',
            title="Revenue by Product Category",
            labels={'x': 'Revenue ($)', 'y': 'Category'},
            color=category_sales.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Top 10 Products")
        top_products = df.groupby('product_name')['total_price'].sum().nlargest(10).sort_values(ascending=True)
        fig = px.bar(
            x=top_products.values,
            y=top_products.index,
            orientation='h',
            title="Top 10 Products by Revenue",
            labels={'x': 'Revenue ($)', 'y': 'Product'},
            color=top_products.values,
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("Sales Trend Over Time")
    daily_sales = df.groupby(df['date'].dt.date)['total_price'].sum()
    fig = px.line(
        x=daily_sales.index,
        y=daily_sales.values,
        title="Daily Sales Trend",
        labels={'x': 'Date', 'y': 'Revenue ($)'},
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Store Performance")
        store_sales = df.groupby('store_id')['total_price'].sum().sort_values(ascending=False)
        fig = px.pie(
            values=store_sales.values,
            names=store_sales.index,
            title="Revenue Distribution by Store"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Category Distribution")
        category_dist = df.groupby('category')['quantity'].sum()
        fig = px.pie(
            values=category_dist.values,
            names=category_dist.index,
            title="Units Sold by Category"
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Data file not found. Please generate sample data first.")
