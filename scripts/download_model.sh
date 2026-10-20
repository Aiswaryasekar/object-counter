#!/usr/bin/env bash
# Downloads the SSD MobileNet V2 (COCO) model and lays it out the way
# TensorFlow Serving expects: tmp/model/<model_name>/<version>/saved_model.pb
set -euo pipefail

MODEL_NAME="${MODEL_NAME:-ssd_mobilenet_v2}"
MODEL_VERSION="${MODEL_VERSION:-1}"
MODEL_URL="http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz"
ARCHIVE_DIR="ssd_mobilenet_v2_coco_2018_03_29"

TARGET_DIR="tmp/model/${MODEL_NAME}/${MODEL_VERSION}"

if [ -f "${TARGET_DIR}/saved_model.pb" ]; then
    echo "Model already present at ${TARGET_DIR}, skipping download."
    exit 0
fi

mkdir -p "${TARGET_DIR}"
curl -fL -o tmp/model.tar.gz "${MODEL_URL}"
tar -xzf tmp/model.tar.gz -C tmp/model
mv "tmp/model/${ARCHIVE_DIR}/saved_model/saved_model.pb" "${TARGET_DIR}/"
rm -rf tmp/model.tar.gz "tmp/model/${ARCHIVE_DIR}"

echo "Model ready at ${TARGET_DIR}"