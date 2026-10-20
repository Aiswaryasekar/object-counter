import io
import json
from unittest.mock import patch, Mock

import numpy as np
import pytest
from PIL import Image

from counter.adapters.object_detector import TFSObjectDetector

WIDTH, HEIGHT = 40, 30

TFS_RESPONSE = {'predictions': [{'num_detections': 1.0,
                                 'detection_boxes': [[0.1, 0.2, 0.3, 0.4]],
                                 'detection_scores': [0.9],
                                 'detection_classes': [1.0]}]}


def image_with_mode(mode: str, image_format: str) -> io.BytesIO:
    image = io.BytesIO()
    Image.new(mode, (WIDTH, HEIGHT)).save(image, image_format)
    image.seek(0)
    return image


@pytest.fixture
def tfs_post():
    with patch('counter.adapters.object_detector.requests.post') as post:
        post.return_value = Mock(json=Mock(return_value=TFS_RESPONSE))
        yield post


def sent_instances(tfs_post) -> np.ndarray:
    sent_body = tfs_post.call_args.kwargs['data']
    return np.array(json.loads(sent_body)['instances'])


@pytest.mark.parametrize('mode, image_format', [('RGB', 'JPEG'),
                                                ('RGBA', 'PNG'),
                                                ('L', 'JPEG'),
                                                ('P', 'PNG')])
def test_every_image_mode_is_sent_to_the_model_as_rgb(tfs_post, mode, image_format):
    TFSObjectDetector('localhost', 8501, 'model').predict(image_with_mode(mode, image_format))

    assert sent_instances(tfs_post).shape == (1, HEIGHT, WIDTH, 3)


def test_converts_model_response_to_predictions(tfs_post):
    predictions = TFSObjectDetector('localhost', 8501, 'model').predict(image_with_mode('RGB', 'JPEG'))

    assert len(predictions) == 1
    assert predictions[0].class_name == 'person'
    assert predictions[0].score == 0.9
    assert (predictions[0].box.xmin, predictions[0].box.ymin) == (0.2, 0.1)
    assert (predictions[0].box.xmax, predictions[0].box.ymax) == (0.4, 0.3)