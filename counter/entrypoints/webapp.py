from io import BytesIO

from flask import Flask, request, jsonify
from PIL import Image, UnidentifiedImageError

from counter import config


class InvalidRequest(Exception):
    """The caller sent something we cannot work with (answered with HTTP 400)."""


def create_app():

    app = Flask(__name__)

    count_action = config.get_count_action()
    predictions_action = config.get_predictions_action()

    @app.errorhandler(InvalidRequest)
    def handle_invalid_request(error):
        return jsonify(error=str(error)), 400

    @app.route('/object-count', methods=['POST'])
    def object_detection():
        image, threshold = read_image_and_threshold()
        count_response = count_action.execute(image, threshold)
        return jsonify(count_response)

    @app.route('/predictions', methods=['POST'])
    def predictions():
        image, threshold = read_image_and_threshold()
        return jsonify(predictions_action.execute(image, threshold))

    return app


def read_image_and_threshold():
    return read_image(), read_threshold()


def read_threshold() -> float:
    raw_threshold = request.form.get('threshold', 0.5)
    try:
        threshold = float(raw_threshold)
    except ValueError:
        raise InvalidRequest(f"threshold must be a number between 0 and 1, got '{raw_threshold}'")
    if not 0 <= threshold <= 1:
        raise InvalidRequest(f"threshold must be between 0 and 1, got {threshold}")
    return threshold


def read_image() -> BytesIO:
    if 'file' not in request.files:
        raise InvalidRequest("an image must be sent in the multipart form field 'file'")
    image = BytesIO()
    request.files['file'].save(image)
    ensure_is_image(image)
    return image


def ensure_is_image(image: BytesIO):
    try:
        Image.open(image).verify()
    except (UnidentifiedImageError, OSError):
        raise InvalidRequest("the uploaded file is not a valid image")
    finally:
        image.seek(0)


if __name__ == '__main__':
    app = create_app()
    app.run('0.0.0.0', debug=True)