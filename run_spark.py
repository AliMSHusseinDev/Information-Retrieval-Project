"""Reproducible preprocessing entry point. Spark is never started by a web request."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from src.indexing import build_index, read_documents, dataset_fingerprint
from src.calculations import calculate_collection
from src.exports import export_all
from src.storage import SCHEMA_VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', default='local[2]', help='Spark master (default: two local workers)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    documents = read_documents(root / 'data')
    index, spark_version = build_index(root / 'data', args.master)
    model = dict(documents=documents, index=index, **calculate_collection(index, documents))
    model['metadata'] = dict(schema_version=SCHEMA_VERSION, engine='Apache Spark / PySpark',
                             spark_version=spark_version, master=args.master,
                             fingerprint=dataset_fingerprint(root / 'data'),
                             generated_at=datetime.now(timezone.utc).isoformat())
    export_all(model, root / 'outputs')
    print(f'Spark {spark_version}: {len(documents)} documents, {len(index)} terms, '
          f'{sum(len(text.split()) for text in documents.values())} tokens. Outputs saved.')


if __name__ == '__main__':
    main()
