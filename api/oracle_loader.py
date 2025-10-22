import os
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables from .env file in parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def _read_csv_text(text: str) -> pd.DataFrame:
    return pd.read_csv(StringIO(text))


def load_via_par(par_url: str) -> pd.DataFrame:
    response = requests.get(par_url, timeout=30)
    response.raise_for_status()
    return _read_csv_text(response.text)


def load_via_oci(namespace: str, bucket: str, obj_name: str) -> pd.DataFrame:
    try:
        import oci  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("OCI SDK not installed. Install 'oci' to enable this loader.") from exc

    config_file = os.getenv("OCI_CONFIG_FILE", oci.config.DEFAULT_LOCATION)
    profile = os.getenv("OCI_CONFIG_PROFILE", oci.config.DEFAULT_PROFILE)
    try:
        config = oci.config.from_file(file_location=config_file, profile_name=profile)
    except Exception as exc:  # pragma: no cover - depends on env setup
        raise RuntimeError("Unable to load OCI configuration. Verify OCI config file and profile.") from exc

    client = oci.object_storage.ObjectStorageClient(config=config)
    response = client.get_object(namespace_name=namespace, bucket_name=bucket, object_name=obj_name)
    data = getattr(response.data, "content", None)
    if data is None and hasattr(response.data, "read"):
        data = response.data.read()
    if data is None and hasattr(response.data, "text"):
        data = response.data.text
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    if not isinstance(data, str):  # pragma: no cover - depends on SDK
        raise RuntimeError("Unexpected OCI response format")
    return _read_csv_text(data)


def load_via_s3(
    endpoint: str,
    key: str,
    secret: str,
    bucket: str,
    keyname: str,
) -> pd.DataFrame:
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("boto3 not installed. Install 'boto3' to enable this loader.") from exc

    session = boto3.session.Session(
        aws_access_key_id=key,
        aws_secret_access_key=secret,
    )
    client = session.client("s3", endpoint_url=endpoint)
    response = client.get_object(Bucket=bucket, Key=keyname)
    content = response["Body"].read().decode("utf-8")
    return _read_csv_text(content)


def select_source() -> pd.DataFrame:
    par_url = os.getenv("ORACLE_PAR_URL")
    if par_url:
        return load_via_par(par_url)

    if os.getenv("ORACLE_OCI") == "1":
        namespace = _require_env("NAMESPACE")
        bucket = _require_env("BUCKET")
        obj_name = _require_env("OBJECT")
        return load_via_oci(namespace, bucket, obj_name)

    if os.getenv("ORACLE_S3") == "1":
        endpoint = _require_env("ORACLE_S3_ENDPOINT")
        access_key = _require_env("ORACLE_S3_KEY")
        secret_key = _require_env("ORACLE_S3_SECRET")
        bucket = _require_env("ORACLE_S3_BUCKET")
        keyname = os.getenv("ORACLE_S3_KEYNAME", "products.csv")
        return load_via_s3(endpoint, access_key, secret_key, bucket, keyname)

    local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "products.csv"))
    return pd.read_csv(local_path)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required for the selected loader.")
    return value
