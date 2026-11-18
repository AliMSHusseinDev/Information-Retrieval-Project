"""Rebuild the Technology reference exports for offline validation."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from src.indexing import build_index, read_documents, dataset_fingerprint
from src.calculations import calculate_collection
from src.exports import export_all
from src.storage import SCHEMA_VERSION


def build_reference(root, output_dir, master='local[2]'):
    documents = read_documents(root / 'data' / '2. Technology')
    index, spark_version = build_index(root / 'data' / '2. Technology', master)
    model = dict(documents=documents, index=index, **calculate_collection(index, documents))
    model['metadata'] = dict(schema_version=SCHEMA_VERSION, engine='Apache Spark / PySpark',
                             spark_version=spark_version, master=master,
                             fingerprint=dataset_fingerprint(root / 'data' / '2. Technology'),
                             generated_at=datetime.now(timezone.utc).isoformat())
    export_all(model, output_dir)
    print(f'Spark {spark_version}: {len(documents)} documents, {len(index)} terms, '
          f'{sum(len(text.split()) for text in documents.values())} tokens. Outputs saved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', default='local[2]', help='Spark master (default: two local workers)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    build_reference(root, root / 'artifacts' / 'technology', args.master)


if __name__ == '__main__':
    main()
