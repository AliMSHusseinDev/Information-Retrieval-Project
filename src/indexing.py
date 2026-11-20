"""Part A: build positions on real Apache Spark workers, then collect a small index."""

import hashlib
import re
from pathlib import Path


def document_number(document_id):
    """Return the numeric part of d1, ..., d10 for natural document sorting."""
    return int(document_id[1:])


def read_documents(data_dir):
    """Read d<number>.txt files without changing the original text or token order."""
    paths = [path for path in Path(data_dir).glob('*.txt')
             if re.fullmatch(r'd[1-9]\d*', path.stem)]
    paths.sort(key=lambda path: document_number(path.stem))
    if not paths:
        raise ValueError('No d<number>.txt documents found in the data directory.')
    return {path.stem: path.read_text(encoding='utf-8').strip() for path in paths}


def dataset_fingerprint(data_dir):
    """Hash filenames and exact bytes, so even an edited source file invalidates the cache."""
    digest = hashlib.sha256()
    for document_id in read_documents(data_dir):
        digest.update((document_id + '.txt\0').encode())
        digest.update((Path(data_dir) / (document_id + '.txt')).read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def build_index(data_dir, master='local[2]'):
    """Index a local folder using the same Spark pipeline as the web import."""
    return index_documents(read_documents(data_dir), master)


# Member 1: Build the positional index with Spark.
def index_documents(documents, master='local[2]'):
    """Return the word positions for each term and document, plus the Spark version."""
    import json
    import os
    from pyspark.sql import SparkSession, functions

    os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
    spark = (SparkSession.builder.master(master).appName('Document import')
             .config('spark.ui.enabled', 'false').config('spark.sql.shuffle.partitions', '2')
             .getOrCreate())
    try:
        tokenized_documents = [
            {'document_id': document_id, 'words': text.lower().split()}
            for document_id, text in documents.items()
        ]
        document_schema = 'array<struct<document_id:string,words:array<string>>>'
        document_array = functions.from_json(
            functions.lit(json.dumps(tokenized_documents)), document_schema
        )
        document_rows = spark.range(1).select(functions.explode(document_array).alias('document'))
        word_rows = document_rows.select(
            'document.document_id',
            functions.posexplode('document.words').alias('word_offset', 'term')
        )
        # Spark offsets start at 0. Positions in the assignment start at 1.
        word_position = functions.col('word_offset') + 1
        positions_by_term_and_document = word_rows.groupBy('term', 'document_id').agg(
            functions.sort_array(functions.collect_list(word_position)).alias('positions')
        )
        ordered_postings = sorted(
            positions_by_term_and_document.collect(),
            key=lambda posting: (posting.term, document_number(posting.document_id))
        )
        positional_index = {}
        for posting in ordered_postings:
            positional_index.setdefault(posting.term, {})[posting.document_id] = posting.positions
        return positional_index, spark.version
    finally:
        spark.stop()
