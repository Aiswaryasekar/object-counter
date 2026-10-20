import io
import json

import pytest

from pathlib import Path
from counter.entrypoints.webapp import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def image_path():
    ref_dir = Path(__file__).parent
    return ref_dir.parent.parent / "resources" / "images" / "boy.jpg"


def test_object_detection(client, image_path):
    # Load the image from the path resource/boy.jpg
    with open(image_path, 'rb') as f:
        image_data = f.read()
    image = io.BytesIO(image_data)

    data = {
        'threshold': '0.9',
        'model_name': 'ssd_mobilenet_v2',
    }
    data['file'] = (image, 'test.jpg')

    # Make a test request to the object_detection endpoint
    response = client.post('/object-count', data = data,
        content_type='multipart/form-data', buffered=True)

    # Check that the count_action was called with the correct arguments and
    # and status code is correct(Integration test)
    assert response.status_code == 200
    assert json.loads(response.data) != None


def post_image(client, image_path, url, threshold):
    with open(image_path, 'rb') as f:
        data = {'threshold': threshold, 'file': (io.BytesIO(f.read()), 'test.jpg')}
    return client.post(url, data=data, content_type='multipart/form-data', buffered=True)


def test_predictions_returns_class_score_and_box(client, image_path):
    response = post_image(client, image_path, '/predictions', '0.5')

    assert response.status_code == 200
    predictions = json.loads(response.data)
    assert len(predictions) == 1
    assert predictions[0]['class_name'] == 'cat'
    assert predictions[0]['score'] > 0.5
    assert set(predictions[0]['box']) == {'xmin', 'ymin', 'xmax', 'ymax'}


def test_predictions_is_empty_when_threshold_is_too_high(client, image_path):
    response = post_image(client, image_path, '/predictions', '0.9999')

    assert response.status_code == 200
    assert json.loads(response.data) == []