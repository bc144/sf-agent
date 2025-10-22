.PHONY: api-venv ui-venv qdrant-setup ingest api agent ui

api-venv:
	python3 -m venv api/.venv
	api/.venv/bin/pip install --upgrade pip
	api/.venv/bin/pip install -r api/requirements.txt

ui-venv:
	python3 -m venv ui/.venv
	ui/.venv/bin/pip install --upgrade pip
	ui/.venv/bin/pip install -r ui/requirements.txt

qdrant-setup:
	api/.venv/bin/python api/qdrant_setup.py

ingest:
	api/.venv/bin/python api/ingest_csv.py

api:
	api/.venv/bin/uvicorn api.main:app --port 8000 --reload

agent:
	api/.venv/bin/python api/agent_cli.py

ui:
	ui/.venv/bin/streamlit run ui/app.py
