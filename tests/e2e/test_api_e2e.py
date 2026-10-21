"""End to end: real HTTP request -> app -> real TF Serving model -> real PostgreSQL."""
import io
from pathlib import Path

import pytest
import requests
from PIL import Image

pytestmark = pytest.mark.e2e

BOY_PHOTO = Path('resources/images/boy.jpg')
REQUEST_TIMEOUT_SECONDS = 60


def post_image(api_url, endpoint, image_bytes, threshold):
    return requests.post(f'{api_url}{endpoint}',
                         data={'threshold': threshold},
                         files={'file': ('photo', image_bytes)},
                         timeout=REQUEST_TIMEOUT_SECONDS)


def boy_photo_as(mode, image_format):
    converted = io.BytesIO()
    Image.open(BOY_PHOTO).convert(mode).save(converted, image_format)
    return converted.getvalue()


def counts_by_class(object_counts):
    return {object_count['object_class']: object_count['count'] for object_count in object_counts}


def test_predictions_find_a_person_with_a_valid_box(api_url):
    response = post_image(api_url, '/predictions', BOY_PHOTO.read_bytes(), threshold='0.9')

    assert response.status_code == 200
    person = next(p for p in response.json() if p['class_name'] == 'person')
    box = person['box']
    assert person['score'] >= 0.9
    assert 0 <= box['xmin'] < box['xmax'] <= 1
    assert 0 <= box['ymin'] < box['ymax'] <= 1


def test_a_higher_threshold_keeps_only_confident_predictions(api_url):
    response = post_image(api_url, '/predictions', BOY_PHOTO.read_bytes(), threshold='0.6')

    assert [p['class_name'] for p in response.json()] == ['person']


def test_object_count_accumulates_across_requests(api_url):
    photo = BOY_PHOTO.read_bytes()

    first = post_image(api_url, '/object-count', photo, threshold='0.9').json()
    second = post_image(api_url, '/object-count', photo, threshold='0.9').json()

    assert counts_by_class(first['current_objects'])['person'] == 1
    assert counts_by_class(first['total_objects'])['person'] == 1
    assert counts_by_class(second['current_objects'])['person'] == 1
    assert counts_by_class(second['total_objects'])['person'] == 2


@pytest.mark.parametrize('mode, image_format', [('RGBA', 'PNG'), ('L', 'JPEG')])
def test_images_that_are_not_plain_rgb_are_detected(api_url, mode, image_format):
    response = post_image(api_url, '/predictions', boy_photo_as(mode, image_format), threshold='0.5')

    assert response.status_code == 200
    assert 'person' in [p['class_name'] for p in response.json()]


def test_invalid_threshold_is_rejected_with_a_clear_message(api_url):
    response = post_image(api_url, '/object-count', BOY_PHOTO.read_bytes(), threshold='abc')

    assert response.status_code == 400
    assert 'threshold' in response.json()['error']