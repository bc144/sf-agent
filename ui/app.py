import os
from typing import List

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")


def _load_options(column: str) -> List[str]:
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "products.csv"))
    if not os.path.exists(data_path):
        return []

    df = pd.read_csv(data_path)
    if column not in df.columns:
        return []

    unique_values = set()
    for value in df[column].dropna():
        if isinstance(value, str) and ";" in value:
            unique_values.update({item.strip() for item in value.split(";") if item.strip()})
        else:
            text = str(value).strip()
            if text:
                unique_values.add(text)
    return sorted(unique_values)


st.set_page_config(page_title="Product Finder", layout="wide")
st.title("Semantic Product Finder")


categories = ["Any"] + _load_options("category")
colors = ["Any"] + _load_options("colors")
sizes = ["Any"] + _load_options("sizes")


with st.sidebar:
    st.header("Filters")
    category = st.selectbox("Category", categories)
    color = st.selectbox("Color", colors)
    size = st.selectbox("Size", sizes)
    max_price = st.number_input("Max price", min_value=0.0, value=50.0, step=5.0)


query = st.text_input("Search query", "black hoodie under $50 in M")
k = st.slider("Results", min_value=3, max_value=10, value=6)


def _build_constraints():
    constraints = {}
    if category != "Any":
        constraints["category"] = category
    if color != "Any":
        constraints["color"] = color
    if size != "Any":
        constraints["size"] = size
    if max_price:
        constraints["price_max"] = float(max_price)
    return constraints


if st.button("Search"):
    payload = {
        "query": query,
        "constraints": _build_constraints(),
        "k": k,
    }

    try:
        response = requests.post(f"{API_URL}/search", json=payload, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")
    else:
        data = response.json()
        items = data.get("items", [])
        if not items:
            st.warning("No products found. Try relaxing filters.")
        for item in items:
            with st.container():
                cols = st.columns([1, 2])
                with cols[0]:
                    image_url = item.get("image_url")
                    if image_url:
                        st.image(image_url, use_column_width=True)
                with cols[1]:
                    st.subheader(item.get("title", "Product"))
                    st.write(f"**Brand:** {item.get('brand', '-')}")
                    st.write(f"**Category:** {item.get('category', '-')}")
                    price_value = item.get("price")
                    try:
                        price = float(price_value)
                    except (TypeError, ValueError):
                        price = 0.0
                    st.write(f"**Price:** ${price:.2f}")
                    colors_value = item.get("colors") or []
                    if isinstance(colors_value, str):
                        colors_list = [c.strip() for c in colors_value.split(";") if c.strip()]
                    else:
                        colors_list = list(colors_value)
                    sizes_value = item.get("sizes") or []
                    if isinstance(sizes_value, str):
                        sizes_list = [s.strip() for s in sizes_value.split(";") if s.strip()]
                    else:
                        sizes_list = list(sizes_value)
                    st.write(f"**Colors:** {', '.join(colors_list) or '-'}")
                    st.write(f"**Sizes:** {', '.join(sizes_list) or '-'}")
                    if item.get("why"):
                        st.info(item["why"])
