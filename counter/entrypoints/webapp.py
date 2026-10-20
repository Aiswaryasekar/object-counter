from io import BytesIO

from flask import Flask, request, jsonify

from counter import config


def create_app():

    app = Flask(__name__)

    count_action = config.get_count_action()
    predictions_action = config.get_predictions_action()

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
    threshold = float(request.form.get('threshold', 0.5))
    uploaded_file = request.files['file']
    image = BytesIO()
    uploaded_file.save(image)
    return image, threshold


if __name__ == '__main__':
    app = create_app()
    app.run('0.0.0.0', debug=True)