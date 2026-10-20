from unittest.mock import Mock

import pytest

from counter.domain.actions import CountDetectedObjects, ListPredictions
from counter.domain.models import ObjectCount
from tests.domain.helpers import generate_prediction


class TestCountDetectedObjects:
    @pytest.fixture
    def object_detector(self) -> Mock:
        object_detector = Mock()
        object_detector.predict.return_value = [generate_prediction('cat', 0.9),
                                                generate_prediction('cat', 0.8),
                                                generate_prediction('dog', 0.8),
                                                generate_prediction('dog', 0.1),
                                                generate_prediction('rabbit', 0.9)]
        return object_detector

    @pytest.fixture
    def count_object_repo(self) -> Mock:
        return Mock()

    def test_count_valid_predictions(self, object_detector, count_object_repo) -> None:
        response = CountDetectedObjects(object_detector, count_object_repo).execute(None, 0.5)
        assert sorted(response.current_objects, key=lambda x: x.object_class) == \
            [ObjectCount('cat', 2), ObjectCount('dog', 1), ObjectCount('rabbit', 1)]

    def test_update_count_object_repo(self, object_detector, count_object_repo):
        CountDetectedObjects(object_detector, count_object_repo).execute(None, 0)
        count_object_repo.update_values.assert_called_with(
            [ObjectCount('cat', 2), ObjectCount('dog', 2), ObjectCount('rabbit', 1)])


class TestListPredictions:
    @pytest.fixture
    def object_detector(self) -> Mock:
        object_detector = Mock()
        object_detector.predict.return_value = [generate_prediction('cat', 0.9),
                                                generate_prediction('dog', 0.4),
                                                generate_prediction('rabbit', 0.6)]
        return object_detector

    def test_returns_only_predictions_over_threshold(self, object_detector):
        predictions = ListPredictions(object_detector).execute(None, 0.5)
        assert [p.class_name for p in predictions] == ['cat', 'rabbit']

    def test_returns_empty_list_when_nothing_passes(self, object_detector):
        assert ListPredictions(object_detector).execute(None, 0.95) == []

    def test_keeps_score_and_box(self, object_detector):
        prediction = ListPredictions(object_detector).execute(None, 0.8)[0]
        assert prediction == generate_prediction('cat', 0.9)