# Using several internal models

This is a design. I did not build it.

## Where we are

One public model is downloaded by a script and served by one TensorFlow Serving container. The model name comes from an environment variable. The label map (class number to name) is the COCO one, hardcoded in the detector. Counts have no idea which model produced them.

## What I would change

1. **Keep model files out of git.** Store them in a private, versioned place the company already uses (a bucket, Artifactory, or a model registry), and have a script pull them with the caller's credentials and check a checksum. The repo only holds a small file listing which models and versions are in use.
2. **One manifest file** (`models.yaml`) with, for each model: name, version, where it lives, and which label file it uses. The download script, the serving config and the tests all read it, so they cannot disagree.
3. **Serve them with TensorFlow Serving's multi-model config.** One config file lists every model. If a model needs a GPU or has very different traffic, run it in its own container instead.
4. **Let the request choose the model.** Add a `model_name` parameter, check it against the manifest, and keep a default so current callers still work. The detector gets that model's label map instead of loading the COCO one.
5. **Store counts per model.** Add a model column to the table (the primary key becomes model plus class), and put the model name and version in the response and in the logs.
6. **Tests.** The end-to-end tests loop over the manifest and send a reference image to each model.

## Things to watch

- Private models mean access control. The app should only have read access to the models it serves.
- Pin model versions in the manifest and change them through a pull request, so a rollback is a one-line change.
- Splitting counts per model needs a migration for the existing table.

## Other frameworks (option 6b)

I chose option 6a (tests), so I did not implement this. The idea is that each framework gets its own adapter behind the same `ObjectDetector` port and the manifest says which one to use. A server that handles several frameworks, such as Triton, could sit behind one adapter.