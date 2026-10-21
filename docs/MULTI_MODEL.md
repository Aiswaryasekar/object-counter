# Supporting several internally trained models

## Situation today

- One public model is downloaded by script into `tmp/model` and served by one TensorFlow Serving container.
- The model name comes from the `MODEL_NAME` environment variable, so the app can talk to exactly one model.
- The COCO label map (`counter/adapters/mscoco_label_map.json`) is hardcoded in the detector, so class IDs of any other model would be translated wrongly.
- The request form already carries a `model_name` field in a test, but nothing in the API reads it.
- Counts are stored per class only, with no idea which model produced them.

The goal is to add private models without copying them into the repository, without code changes per model, and with every result traceable to a model version.

## What I would change

### 1. Keep models out of git and fetch them from a private registry

Models are build artifacts, not source code. Store them in a private, access-controlled, versioned location (for example an S3 or GCS bucket, Artifactory, or the MLflow model registry, whichever the company already uses). `make model` becomes `make models`: it reads a manifest (next point), downloads each listed model with the caller's credentials, verifies a checksum, and lays them out as `tmp/models/<name>/<version>/`. Credentials come from the environment or a secret manager, never from the repo.

### 2. One manifest as the single source of truth

`models.yaml`, checked into git (it contains no secrets or weights):

```yaml
models:
  - name: shelf_detector
    version: 3
    framework: tensorflow
    source: s3://company-models/shelf_detector/3/
    sha256: <checksum>
    labels: models/shelf_detector/labels.json
  - name: price_tag_detector
    version: 1
    framework: tensorflow
    source: s3://company-models/price_tag_detector/1/
    sha256: <checksum>
    labels: models/price_tag_detector/labels.json
```

The download script, the TF Serving configuration, the API's list of allowed models and the tests are all generated from or checked against this one file, so they cannot drift apart.

### 3. Serve all models from TensorFlow Serving

TF Serving can host many models in one process. Replace the stale `tmp/model/model_config.config` (it names `rfcn`) with a generated file:

```
model_config_list {
  config { name: "shelf_detector"      base_path: "/models/shelf_detector"      model_platform: "tensorflow" }
  config { name: "price_tag_detector"  base_path: "/models/price_tag_detector"  model_platform: "tensorflow" }
}
```

Start the container with `--model_config_file=/models/models.config` (and `--model_config_file_poll_wait_seconds=60` to pick up new versions without a restart). The existing health check, `GET /v1/models/<name>`, reports whether each model is `AVAILABLE`.

When models have very different resource needs (GPU versus CPU, or very different traffic), run one TF Serving container per model instead, and give each its own host in the manifest. The application code stays the same.

### 4. Code changes in the application

- **API:** `model_name` (and optionally `model_version`) becomes a request parameter. Names are validated against the manifest; an unknown model returns a 404 or 400 with the list of valid names. A default model keeps current clients working.
- **Detector:** `TFSObjectDetector` already receives the model name; it should also receive that model's label map instead of loading the COCO file itself. A small factory, `ObjectDetectorFactory.for_model(name)`, builds and caches one detector per model. The domain only sees the existing `ObjectDetector` port.
- **Label maps:** one `labels.json` per model, stored next to the model and listed in the manifest.
- **Counts:** add a `model` column, with primary key `(model, object_class)`, so a person counted by one model is not mixed with the other's. This needs a small migration for PostgreSQL and a compound key for MongoDB. The response includes `model` and `model_version` so every number can be traced.
- **Config:** each model's settings (host, threshold default, label file) come from the manifest, not from `if` statements.

### 5. Tests and automation

- The end-to-end tests are parameterised over the manifest: for every model, send a reference image and assert the expected classes. A model that regresses or is missing fails CI.
- `make up` starts TF Serving with the generated config; `make models` is idempotent (skips what is already present and valid).
- CI pulls models with a read-only service account, and never prints credentials.

### 6. Governance

- Private models are access-controlled at the registry; the app's service account gets read-only access to exactly the models it serves.
- Pin model versions in the manifest, and promote a new version through a pull request, so the deployed model is always reviewable and reversible.
- Record the model name and version in logs and in responses.

## Trade-offs

| Decision | Benefit | Cost |
|---|---|---|
| One TF Serving for all models | One thing to run, simple compose file | Models compete for memory and CPU; one crash affects all |
| One container per model | Isolation, independent scaling and GPUs | More containers and ports to manage |
| Manifest in git | Reviewable, reproducible deployments | Another file to keep correct; needs a validation step |
| Counts per model | Clean, comparable numbers | Schema migration and a change to the response |

## Suggested order of work

1. Introduce the manifest and make `make models` read it.
2. Generate the TF Serving config from it and serve two models.
3. Add the `model_name` parameter, the detector factory and per-model label maps.
4. Add the `model` column to the repositories.
5. Extend the end-to-end tests to loop over the manifest.

## Other frameworks

This design also prepares for models built with other frameworks (PyTorch, ONNX): the manifest already has a `framework` field, and each framework needs one new adapter implementing the same `ObjectDetector` port, chosen by the factory. A serving layer that supports several frameworks (for example NVIDIA Triton) would let all models share one URL scheme, but that is outside the scope of this exercise.
