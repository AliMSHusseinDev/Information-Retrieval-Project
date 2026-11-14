"""Load saved Spark results and reject missing, incompatible, or stale artifacts."""

import json
from src.indexing import dataset_fingerprint

SCHEMA_VERSION = 1


def load_model(root):
    """Load the saved model only if its dataset hash and pipeline version match."""
    try:
        model = json.loads((root / 'outputs' / 'model.json').read_text(encoding='utf-8'))
        if model['metadata']['schema_version'] != SCHEMA_VERSION:
            raise ValueError('Processing format changed.')
        if model['metadata']['fingerprint'] != dataset_fingerprint(root / 'data'):
            raise ValueError('The dataset has changed since preprocessing.')
        return model
    except (OSError, ValueError, KeyError) as error:
        raise RuntimeError(f'{error} Run python run_spark.py to rebuild the outputs.') from error
