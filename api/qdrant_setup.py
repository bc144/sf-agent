import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.exceptions import UnexpectedResponse

# Load environment variables from .env file in parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


COLLECTION_NAME = "products"
VECTOR_NAME = "text"
VECTOR_SIZE = 384


def _build_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_CLIENT")
    if url:
        return QdrantClient(url=url, api_key=api_key)
    return QdrantClient(host="localhost", port=6333)


def ensure_collection(client: Optional[QdrantClient] = None) -> QdrantClient:
    client = client or _build_client()
    vectors_config = {
        VECTOR_NAME: rest.VectorParams(size=VECTOR_SIZE, distance=rest.Distance.COSINE),
    }

    if not client.collection_exists(collection_name=COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=vectors_config,
        )
        print(f"Created collection '{COLLECTION_NAME}'")
    else:
        print(f"Collection '{COLLECTION_NAME}' already exists")

    _ensure_payload_indexes(client)
    return client


def _ensure_payload_indexes(client: QdrantClient) -> None:
    indexes = {
        "category": rest.PayloadSchemaType.KEYWORD,
        "brand": rest.PayloadSchemaType.KEYWORD,
        "colors": rest.PayloadSchemaType.KEYWORD,
        "sizes": rest.PayloadSchemaType.KEYWORD,
        "in_stock": rest.PayloadSchemaType.BOOL,
        "price": rest.PayloadSchemaType.FLOAT,
    }

    for field, schema_type in indexes.items():
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=schema_type,
            )
        except UnexpectedResponse:
            continue


if __name__ == "__main__":
    ensure_collection()
