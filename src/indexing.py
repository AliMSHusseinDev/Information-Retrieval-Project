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


def emit_positions(file_record):
    """Spark flatMap worker: emit ((term, document), 1-based position) records."""
    filename, text = file_record
    document_id = filename.replace('\\', '/').rsplit('/', 1)[-1][:-4]
    return [((term, document_id), position)
            for position, term in enumerate(text.lower().split(), start=1)]


def build_index(data_dir, master='local[2]'):
    """Read files with wholeTextFiles and group all positions using Spark RDDs.

    Input: a folder of d<number>.txt files. Output: sorted term -> doc -> positions,
    plus Spark version. Only the finished small index is collected to the driver.
    """
    from pyspark.sql import SparkSession

    documents = read_documents(data_dir)
    spark = (SparkSession.builder.master(master).appName('TechnologyPositionalIndex')
             .config('spark.ui.enabled', 'false').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    try:
        files = spark.sparkContext.wholeTextFiles(Path(data_dir).resolve().as_uri() + '/*.txt')
        grouped = files.flatMap(emit_positions).groupByKey().mapValues(lambda values: sorted(values))
        records = grouped.collect()
        index = {}
        for (term, doc), positions in sorted(records, key=lambda row: (row[0][0], document_number(row[0][1]))):
            if doc in documents:
                index.setdefault(term, {})[doc] = positions
        return index, spark.version
    finally:
        spark.stop()
