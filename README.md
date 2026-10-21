# Object Counter

A Flask API that detects objects in an image with a TensorFlow object-detection model and keeps a running count per class. It also returns the individual predictions (class, score, bounding box).

It is built with a **hexagonal (ports & adapters) architecture**, so the model server and the database can be swapped without touching the business logic.

```
HTTP request
    │
    ▼
entrypoints/   Flask API: reads and validates the request, returns JSON
    │
    ▼
domain/        Business rules: filter by threshold, count per class.
    │          Knows only the abstract ports (ObjectDetector, ObjectCountRepo)
    ▼
adapters/      TF Serving detector · MongoDB repo · PostgreSQL repo · fakes for development
    │
    ▼
TensorFlow Serving (Docker)        MongoDB or PostgreSQL (Docker)
```

## Endpoints

Both endpoints take a multipart form with an image in `file` and an optional `threshold` between 0 and 1 (default `0.5`).

| Endpoint | Returns |
|---|---|
| `POST /object-count` | Objects found in this image (`current_objects`) and the running totals (`total_objects`) |
| `POST /predictions` | Every prediction at or above the threshold: `class_name`, `score` and `box` (`xmin`, `ymin`, `xmax`, `ymax` as fractions of the image, 0 to 1) |

```bash
curl -F "threshold=0.6" -F "file=@resources/images/boy.jpg" http://localhost:5000/predictions
```
```json
[{"box": {"xmax": 0.54, "xmin": 0.37, "ymax": 0.81, "ymin": 0.35}, "class_name": "person", "score": 0.99}]
```

Invalid input (non-numeric or out-of-range threshold, missing file, file that is not an image) returns **400** with `{"error": "..."}`.

## Prerequisites

- Python 3.10 or newer
- Docker (Docker Desktop on Windows/macOS)
- `make` (optional, see the manual commands below if you do not have it; on Windows use WSL or Git Bash)
- I developed this on Windows and used the manual commands. The Makefile was only dry-run checked, not tried on Linux or macOS

## Quick start

```bash
make install     # virtualenv + dependencies
make model       # downloads the SSD MobileNet V2 (COCO) model into tmp/model
make up          # TF Serving, MongoDB and PostgreSQL in Docker
make run-prod    # API against the real services (MongoDB)
```

To store the counts in PostgreSQL instead of MongoDB:
```bash
DB_BACKEND=postgres make run-prod
```

No Docker at all? `make run` starts the API with fakes: a fake detector that always reports one cat, and in-memory counts. Useful to explore the API, but it ignores the image content.

All commands: `make help`.

| Command | What it does |
|---|---|
| `make install` | Creates `.venv` and installs `requirements.txt` |
| `make model` | Downloads and lays out the model (skipped if already present) |
| `make up` / `make down` / `make logs` | Start, stop and follow the Docker services |
| `make run` | API with fakes |
| `make run-prod` | API with the real model server and database |
| `make test` | Fast tests (no Docker needed) |
| `make test-e2e` | End-to-end tests against the real model and PostgreSQL (run `make up` first) |
| `make clean` | Removes the virtualenv, caches and debug images |

## Manual setup (without `make`)

### 1. Download the model

Unix:
```bash
bash scripts/download_model.sh
```

Windows (PowerShell):
```powershell
mkdir tmp\model\ssd_mobilenet_v2\1
curl.exe -L -o tmp\model.tar.gz http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz
tar -xzf tmp\model.tar.gz -C tmp\model
move tmp\model\ssd_mobilenet_v2_coco_2018_03_29\saved_model\saved_model.pb tmp\model\ssd_mobilenet_v2\1\
```

You should end up with `tmp/model/ssd_mobilenet_v2/1/saved_model.pb`.

### 2. Start the services

```bash
docker compose up -d
```
or, one container at a time:

Unix:
```bash
docker run --rm -d --name tfserving -p 8501:8501 \
    --mount type=bind,source=$(pwd)/tmp/model,target=/models \
    -e MODEL_NAME=ssd_mobilenet_v2 tensorflow/serving
docker run --rm -d --name test-mongo -p 27017:27017 mongo:latest
```

Windows (PowerShell):
```powershell
docker run --rm -d --name=tfserving -p 8501:8501 -v "$pwd\tmp\model:/models" -e MODEL_NAME=ssd_mobilenet_v2 tensorflow/serving
docker run --rm -d --name test-mongo -p 27017:27017 mongo:latest
```

Check the model is loaded (look for `"state": "AVAILABLE"`):
```bash
curl http://localhost:8501/v1/models/ssd_mobilenet_v2
```

### 3. Python environment

Unix:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Run the API

```bash
python -m counter.entrypoints.webapp                  # fakes
ENV=prod python -m counter.entrypoints.webapp         # real services
```
PowerShell: `$env:ENV = "prod"` then `python -m counter.entrypoints.webapp`.

> If you have connectivity problems on Windows, try `127.0.0.1` instead of `localhost`.

## Configuration

Everything is configured with environment variables. The defaults match `docker-compose.yml`.

| Variable | Default | Meaning |
|---|---|---|
| `ENV` | `dev` | `dev` uses fakes; `prod` uses the real services |
| `DB_BACKEND` | `mongo` | `mongo` or `postgres` (only used when `ENV=prod`) |
| `TFS_HOST`, `TFS_PORT` | `localhost`, `8501` | TensorFlow Serving REST endpoint |
| `MODEL_NAME` | `ssd_mobilenet_v2` | Model served by TensorFlow Serving |
| `MONGO_HOST`, `MONGO_PORT`, `MONGO_DB` | `localhost`, `27017`, `prod_counter` | MongoDB |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `localhost`, `5432`, `counter`, `counter`, `counter` | PostgreSQL (the table is created on startup) |

The credentials in `docker-compose.yml` are for local development only.

## Tests

```bash
make test          # or: python -m pytest
make test-e2e      # or: python -m pytest -m e2e   (needs TF Serving and PostgreSQL running)
```

| Kind | Where | Needs Docker |
|---|---|---|
| Unit: domain logic, with mocks | `tests/domain` | no |
| API: Flask test client, fakes | `tests/entrypoints` | no |
| Adapter: detector against a mocked TF Serving | `tests/adapters/test_object_detector.py` | no |
| Contract: the same tests run against the in-memory and PostgreSQL repos | `tests/adapters/test_count_repo_contract.py` | PostgreSQL (skipped if it is down) |
| End to end: real app, real model, real PostgreSQL | `tests/e2e` | TF Serving and PostgreSQL |

The PostgreSQL contract tests use the database `counter_test` and the end-to-end tests use `counter_e2e`, so your own data is never touched.

## Project layout

```
counter/
  domain/        models, ports (interfaces), actions (use cases), prediction rules
  adapters/      object_detector.py, count_repo.py (in-memory, MongoDB), postgres_count_repo.py
  entrypoints/   webapp.py (Flask API), main.py (command line)
  config.py      chooses and builds the implementations from environment variables
  debug.py       draws predictions on images into tmp/debug (development aid)
tests/           see the table above
scripts/         download_model.sh
docs/            IMPROVEMENTS.md, MULTI_MODEL.md
Makefile  docker-compose.yml  pytest.ini  requirements.txt
```

## More documentation

- [docs/IMPROVEMENTS.md](docs/IMPROVEMENTS.md): code review, what was fixed, what is proposed next
- [docs/MULTI_MODEL.md](docs/MULTI_MODEL.md): how to support several internally trained models
