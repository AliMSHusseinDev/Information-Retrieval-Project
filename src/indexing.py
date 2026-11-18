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
    for doc in read_documents(data_dir):
        digest.update((doc + '.txt\0').encode())
        digest.update((Path(data_dir) / (doc + '.txt')).read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def build_index(data_dir, master='local[2]'):
    """Index a local folder using the same Spark pipeline as the web import."""
    return index_documents(read_documents(data_dir), master)


def index_documents(documents, master='local[2]'):
    """Group positions in Spark SQL directly from the selected text, including on Windows."""
    import json
    import os
    from pyspark.sql import SparkSession, functions as F

    os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
    spark = (SparkSession.builder.master(master).appName('Document import')
             .config('spark.ui.enabled', 'false').config('spark.sql.shuffle.partitions', '2')
             .getOrCreate())
    try:
        batch = [{'doc': doc, 'tokens': text.lower().split()} for doc, text in documents.items()]
        parsed = F.from_json(F.lit(json.dumps(batch)), 'array<struct<doc:string,tokens:array<string>>>')
        docs = spark.range(1).select(F.explode(parsed).alias('entry'))
        terms = docs.select('entry.doc', F.posexplode('entry.tokens').alias('offset', 'term'))
        postings = terms.groupBy('term', 'doc').agg(
            F.sort_array(F.collect_list(F.col('offset') + 1)).alias('positions'))
        index = {}
        for row in sorted(postings.collect(), key=lambda r: (r.term, document_number(r.doc))):
            index.setdefault(row.term, {})[row.doc] = row.positions
        return index, spark.version
    finally:
        spark.stop()
