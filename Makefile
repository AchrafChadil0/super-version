lint:
	poetry run ruff check src/ --fix
lint-c: #check
	poetry run ruff check src/
format:
	poetry run black src/
format-c: #check
	poetry run black --check src/

dev:
	python -m src.core.main dev

start:
	python -m src.core.main start

console:
	python -m src.core.main console

download:
	python -m src.core.main download-files


api:
	 uvicorn src.core.api:app --host 0.0.0.0 --port 8001
oapi:
	uvicorn src.devaito.main:app --host 0.0.0.0 --port 8002
server:
	python -m src.core.server