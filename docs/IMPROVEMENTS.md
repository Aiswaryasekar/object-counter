# Code review and improvements

## How this review was done

I read every file, ran the application with the fakes and against the real model server and MongoDB, and tried inputs the happy path never uses (PNG with transparency, grayscale, a text threshold). Items marked **reproduced** were seen failing on the original code. Items marked **from code review** were read in the code but not exercised.

## Implemented in this submission

| # | Problem | Evidence | Fix |
|---|---|---|---|
| 1 | PNGs with transparency and grayscale images crash the detector | **Reproduced.** `ValueError: cannot reshape array of size 1139200 into shape (445,640,3)`. That is 445 × 640 pixels × 4 channels (RGBA); the code hardcoded 3 | Images are converted to RGB before they are sent to the model (`object_detector.py`). Also replaces a slow pixel-by-pixel copy with one call |
| 2 | The debug drawing breaks on the same images | **Reproduced** in fake mode: it saves a JPEG, which cannot hold transparency | The image is converted to RGB before drawing (`debug.py`) |
| 3 | Invalid input returns a 500 with a stack trace | **Reproduced.** `threshold=abc` gave `ValueError: could not convert string to float` and HTTP 500 | Requests are validated and answered with HTTP 400 and a JSON message: bad or out-of-range threshold, missing `file`, file that is not an image (`webapp.py`) |
| 4 | Setup was a long list of manual, Linux-only commands | README review | `Makefile`, `docker-compose.yml` (TF Serving, MongoDB, PostgreSQL) and `scripts/download_model.sh`; the README explains both the `make` path and the manual commands for Unix and Windows |
| 5 | README pointed to an OpenImages model page, but the downloaded model is the COCO one | README vs. download URL and label map | README now describes the model that is actually used |
| 6 | Only one storage backend | Task 2 | PostgreSQL adapter and a `DB_BACKEND` switch with a clear error for unknown values |
| 7 | Little test coverage of adapters and no end-to-end test | 5 tests, all on fakes | 47 fast tests plus 6 end-to-end tests; the repo contract tests run the same checks on both repo implementations; `pytest.ini` keeps slow tests opt-in (`make test-e2e`) |

## Proposed next, in priority order

### Correctness and robustness

1. **TF Serving call has no timeout and no status check** (`object_detector.py`, the `requests.post` call). A slow or failing model server hangs the request or produces a confusing `KeyError`. *Proposal:* set a timeout, call `raise_for_status()`, and translate failures into a domain error the API answers with 502/503. *Effort: small.* *(from code review)*

2. **The in-memory repo returns `None` for unknown classes.** **Reproduced:** `read_values(['cat', 'dog'])` after storing only `cat` returns `[ObjectCount('cat', 1), None]`, while the MongoDB and PostgreSQL repos simply omit the missing class. The adapters should obey one contract. *Proposal:* return only existing classes and add that case to the contract tests. *Effort: small.*

3. **Threshold semantics.** The requirement says scores that *exceed* the threshold; `over_threshold` keeps scores `>=` it (`predictions.py`). Both endpoints share it, so they are at least consistent. *Proposal:* agree on one definition and name it in the API documentation. *Effort: trivial.* *(from code review)*

4. **No upload size limit.** Flask accepts arbitrarily large files. *Proposal:* set `MAX_CONTENT_LENGTH` and answer 413. *Effort: trivial.* *(from code review)*

5. **Debug drawing runs on every request and lives in the domain.** `actions.py` imports `counter.debug` (PIL, file system) and writes two images per call, which breaks the rule that the domain knows no infrastructure. *Proposal:* move it behind a small port or decorator, enabled only by an environment variable such as `DEBUG_IMAGES=1`. *Effort: medium.* *(from code review)*

### Security and deployment

6. **`debug=True` on `0.0.0.0`** in `webapp.py` exposes Flask's interactive debugger on every network interface; it is protected only by a PIN, which is not acceptable outside a developer machine. *Proposal:* bind to `127.0.0.1` by default, make debug an opt-in flag, and serve with a production WSGI server (gunicorn, waitress) in a Dockerfile. *Effort: small.* *(from code review)*

7. **No container for the app itself.** Compose runs only the dependencies. *Proposal:* add a Dockerfile and an `app` service so `make up` is the whole system. *Effort: small.*

### Performance

8. **A new database connection per call.** `CountMongoDBRepo` creates a `MongoClient` inside every read and write (`count_repo.py`), and the PostgreSQL repo opens a connection per call. *Proposal:* a long-lived `MongoClient` and a connection pool (`psycopg_pool`). *Effort: small.* *(from code review)*

9. **Large JSON payload to TF Serving.** The full pixel array is sent as a nested JSON list. *Proposal:* use the gRPC API (binary) or resize large images before sending. *Effort: medium; measure first.* *(from code review)*

### Maintainability

10. **`config.py` chooses implementations with `globals()[f"{env}_count_action"]`.** A typo in `ENV` gives a `KeyError`. *Proposal:* an explicit dictionary of environments with a readable error. *Effort: trivial.*

11. **`print()` instead of logging** in the detector, and no health check. *Proposal:* `logging` with levels, plus `GET /health` that also checks the model server and the database. *Effort: small.*

12. **`tmp/model/model_config.config` is stale.** It names a model `rfcn`, which is not what the README or the compose file use. *Proposal:* replace it with the multi-model configuration in [MULTI_MODEL.md](MULTI_MODEL.md), or delete it. *Effort: trivial.*

13. **No linting, formatting, type checks or CI.** *Proposal:* `ruff` and `mypy` targets in the Makefile and a GitHub Actions workflow that runs `make test` (and `make test-e2e` with Docker services). `requirements-dev.txt` to separate test tools from runtime dependencies. *Effort: small.*

14. **Weak typing at the boundary.** `execute(image, threshold)` has no types; the image is a `BytesIO`. *Proposal:* annotate, and give the domain its own `Image` type so the core does not depend on a Flask or PIL object. *Effort: small.*

### Behaviour worth discussing

15. **Update then read is two separate steps** in `CountDetectedObjects.execute`. Under concurrent requests, `total_objects` can include another request's counts. That is acceptable for a running total, but it should be a deliberate decision, not an accident.

16. **Counts are global.** There is no notion of who sent the image, or which model produced the count. See [MULTI_MODEL.md](MULTI_MODEL.md) for how counts could be keyed per model.

## What I would do first with another day

Items 1, 2, 6 and 8: they are small, they protect against real failures, and each comes with an easy test.
