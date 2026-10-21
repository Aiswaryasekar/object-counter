# Review and improvements

I ran the original code first, with the fakes and then with the real model, and tried inputs the happy path never uses. Items marked "reproduced" failed when I ran them. Items marked "from reading" I only saw in the code and did not run.

## What I fixed

1. **PNG with transparency and grayscale images crashed.** Reproduced: `cannot reshape array of size 1139200 into shape (445,640,3)`. That is 445 x 640 pixels x 4 channels. The code assumed 3 (RGB). The detector now converts every image to RGB first. The debug drawing had the same problem, so I fixed it there too.
2. **A bad threshold gave a 500 error.** Reproduced with `threshold=abc`. The API now returns 400 with a clear message for a bad or out-of-range threshold, a missing file, or a file that is not an image.
3. **Setup was a long list of manual commands.** I added a Makefile, a docker-compose file and a model download script, and rewrote the README (it also linked to a different model than the one it downloads).
4. **Tests.** I added tests for the new endpoint, for the detector with different image types, a contract test that runs the same checks on the in-memory and PostgreSQL repositories, and a few end-to-end tests that are opt-in (`make test-e2e`).

## What I would do next, in this order

1. **Timeout and error handling on the model call.** There is no timeout and no status check on the request to TensorFlow Serving, so a slow or failing model server hangs the request or gives a confusing error. (from reading)
2. **Make the in-memory repo match the others.** Reproduced: asking it for specific classes returns `None` for a class it has not seen, while MongoDB and PostgreSQL leave it out. The contract tests should cover this.
3. **Turn off Flask debug mode and bind to localhost by default.** It is on, on all interfaces, in `webapp.py`. Add a Dockerfile and a real WSGI server. (from reading)
4. **Connection reuse.** The Mongo adapter creates a client on every call and the PostgreSQL adapter opens a connection on every call. Use one client and a pool. (from reading)
5. **Move the debug image drawing out of the domain.** `actions.py` imports it, so the domain depends on PIL and the file system, and every uploaded image is saved to `tmp/debug`. It should be a switch that is off by default, mainly for privacy. (from reading)
6. **Upload size limit.** (from reading)
7. **Threshold:** the requirement says scores that exceed it, the code keeps scores equal to it. Pick one and say so in the docs.
8. **CI and linting.** A GitHub Actions workflow running the tests, plus ruff. There is none yet.

## Things I did not do or check

- I did not try the Makefile on Linux or macOS. I checked it with a dry run and used the manual commands myself.
- Counts are global. They are not split by model or by customer.
- The PostgreSQL table is created on startup. In a real system I would use migrations.