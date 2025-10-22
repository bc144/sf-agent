import math
from pathlib import Path
from typing import List

import pandas as pd
from dotenv import load_dotenv
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

# Load environment variables from .env file in parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

try:  # pragma: no cover - import shim for script execution
    from .oracle_loader import select_source
    from .qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection
except ImportError:  # pragma: no cover
    from oracle_loader import select_source  # type: ignore
    from qdrant_setup import COLLECTION_NAME, VECTOR_NAME, ensure_collection  # type: ignore


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _to_list(value) -> List[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def _build_document(row: pd.Series, colors: List[str], sizes: List[str]) -> str:
    parts = [row.get("title", ""), row.get("brand", ""), row.get("category", ""), row.get("description", "")]
    colors_text = ", ".join(colors) if colors else "none"
    sizes_text = ", ".join(sizes) if sizes else "none"
    parts.append(f"Colors: {colors_text}")
    parts.append(f"Sizes: {sizes_text}")
    return ". ".join(filter(None, parts))


def main() -> None:
    df = select_source()
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    # Optional: Limit for testing (set to None for full dataset)
    MAX_PRODUCTS = None  # Set to None to load all products
    if MAX_PRODUCTS and len(df) > MAX_PRODUCTS:
        print(f"Limiting to first {MAX_PRODUCTS} products for faster ingestion")
        df = df.head(MAX_PRODUCTS)
    else:
        print(f"Processing all {len(df)} products...")
    
    # Normalize column names - handle both schema types
    if "product_name" in df.columns:
        # Flipkart dataset schema
        df = df.rename(columns={
            'uniq_id': 'product_id',
            'product_name': 'title',
            'discounted_price': 'price',
            'image': 'image_url',
            'product_category_tree': 'category'
        })
        
        # Extract first image URL from array (if it's a string representation of an array)
        def extract_first_image(img_val):
            if pd.isna(img_val) or img_val == "":
                return None
            img_str = str(img_val)
            if img_str.startswith('["') or img_str.startswith("['"):
                # It's a string representation of an array
                import json
                try:
                    img_list = json.loads(img_str.replace("'", '"'))
                    return img_list[0] if img_list else None
                except:
                    return None
            return img_str
        
        df['image_url'] = df['image_url'].apply(extract_first_image)
        
        # Use main_category if available
        if 'main_category' in df.columns:
            df['category'] = df['main_category']
        
        # Add missing columns with defaults
        if 'colors' not in df.columns:
            df['colors'] = ""
        if 'sizes' not in df.columns:
            df['sizes'] = ""
        if 'in_stock' not in df.columns:
            df['in_stock'] = True  # Assume all items are in stock
    
    df = df.fillna("")

    df["in_stock"] = df["in_stock"].apply(_to_bool)
    df["colors"] = df["colors"].apply(_to_list)
    df["sizes"] = df["sizes"].apply(_to_list)
    df["price"] = pd.to_numeric(df["price"], errors='coerce').fillna(0.0)

    documents = [
        _build_document(row, row["colors"], row["sizes"])
        for _, row in df.iterrows()
    ]

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(documents, normalize_embeddings=True)

    client = ensure_collection()

    points = []
    for (_, row), vector in zip(df.iterrows(), embeddings):
        payload = {
            "product_id": row.get("product_id"),
            "title": row.get("title"),
            "brand": row.get("brand") or None,
            "category": row.get("category") or None,
            "price": float(row.get("price", 0.0)),
            "colors": row.get("colors", []),
            "sizes": row.get("sizes", []),
            "image_url": row.get("image_url") or None,
            "description": row.get("description") or None,
            "in_stock": bool(row.get("in_stock", False)),
        }
        points.append(
            rest.PointStruct(
                id=str(row.get("product_id")),
                vector={VECTOR_NAME: vector.tolist()},
                payload=payload,
            )
        )

    # Upsert in batches to avoid payload size limits
    if points:
        BATCH_SIZE = 100  # Upsert 100 products at a time
        total_points = len(points)
        print(f"\nUpserting {total_points} products in batches of {BATCH_SIZE}...")
        
        for i in range(0, total_points, BATCH_SIZE):
            batch = points[i:i + BATCH_SIZE]
            client.upsert(collection_name=COLLECTION_NAME, points=batch)
            print(f"Progress: {min(i + BATCH_SIZE, total_points)}/{total_points} products upserted", end='\r')
        
        print(f"\n✅ Successfully upserted {total_points} products!")


if __name__ == "__main__":
    main()
