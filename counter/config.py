import os

from counter.adapters.count_repo import CountMongoDBRepo, CountInMemoryRepo
from counter.adapters.object_detector import TFSObjectDetector, FakeObjectDetector
from counter.domain.actions import CountDetectedObjects, ListPredictions


def __tfs_object_detector() -> TFSObjectDetector:
    tfs_host = os.environ.get('TFS_HOST', 'localhost')
    tfs_port = os.environ.get('TFS_PORT', 8501)
    model_name = os.environ.get('MODEL_NAME', 'ssd_mobilenet_v2')
    return TFSObjectDetector(tfs_host, tfs_port, model_name)


def dev_count_action() -> CountDetectedObjects:
    return CountDetectedObjects(FakeObjectDetector(), CountInMemoryRepo())


def prod_count_action() -> CountDetectedObjects:
    mongo_host = os.environ.get('MONGO_HOST', 'localhost')
    mongo_port = os.environ.get('MONGO_PORT', 27017)
    mongo_db = os.environ.get('MONGO_DB', 'prod_counter')
    return CountDetectedObjects(__tfs_object_detector(),
                                CountMongoDBRepo(host=mongo_host, port=mongo_port, database=mongo_db))


def get_count_action() -> CountDetectedObjects:
    env = os.environ.get('ENV', 'dev')
    count_action_fn = f"{env}_count_action"
    return globals()[count_action_fn]()


def dev_predictions_action() -> ListPredictions:
    return ListPredictions(FakeObjectDetector())


def prod_predictions_action() -> ListPredictions:
    return ListPredictions(__tfs_object_detector())


def get_predictions_action() -> ListPredictions:
    env = os.environ.get('ENV', 'dev')
    predictions_action_fn = f"{env}_predictions_action"
    return globals()[predictions_action_fn]()