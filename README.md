## Demo Setup

### Back-end

```bash
cd demo/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Qdrant Cloud or local: export QDRANT_URL/QDRANT_API_KEY if Cloud
python qdrant_setup.py
# Oracle ingestion (pick ONE path and export envs first):
#   export ORACLE_PAR_URL="https://objectstorage.../p/..."
#   export ORACLE_OCI=1 NAMESPACE="..." BUCKET="..." OBJECT="products.csv"
#   export ORACLE_S3=1 ORACLE_S3_ENDPOINT="..." ORACLE_S3_KEY="..." ORACLE_S3_SECRET="..." ORACLE_S3_BUCKET="..." ORACLE_S3_KEYNAME="products.csv"
python ingest_csv.py
uvicorn main:app --reload --port 8000
```

### Agent (CLI)

```bash
# same venv
pip install pydantic pydantic-ai rich
python agent_cli.py
# Try: "black hoodie under $50 in M"
```

### Front-end

```bash
cd ../../ui
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export API_URL=http://localhost:8000
streamlit run app.py
```
