"""Generate readable full-precision JSON, CSV matrices, and required-query outputs."""

import csv
import json
import tempfile
from pathlib import Path
from src.queries import PRESETS, search

EXPORT_FILES = ['positional_index.json', 'raw_tf.csv', 'weighted_tf.csv', 'df_idf.csv',
                'tfidf.csv', 'document_lengths.csv', 'normalized.csv', 'phrase_queries.json',
                'boolean_queries.json', 'similarities.csv', 'rankings.csv', 'model.json']


def prepare_downloads(directory):
    """Start a new run with an empty export area, retaining earlier downloads."""
    directory.mkdir(parents=True, exist_ok=True)
    existing = [directory / name for name in [*EXPORT_FILES, 'ir-results.zip']
                if (directory / name).is_file()]
    if existing:
        history = directory.parent / 'previous_exports'
        history.mkdir(exist_ok=True)
        previous = Path(tempfile.mkdtemp(prefix='run-', dir=history))
        for path in existing:
            path.rename(previous / path.name)


def save_download(directory, name, data):
    """Replace the selected file only after its complete contents are on disk."""
    handle = tempfile.NamedTemporaryFile(dir=directory, delete=False)
    staged = Path(handle.name)
    try:
        with handle:
            handle.write(data)
        staged.replace(directory / name)
    finally:
        staged.unlink(missing_ok=True)


def write_csv(path, headers, rows):
    """Write a real UTF-8 CSV with a header and unrounded numeric values."""
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(headers)
        writer.writerows(rows)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def export_all(model, output_dir, presets=PRESETS):
    """Save every mandatory calculation and all four freshly calculated queries."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'model.json', model)
    write_json(output / 'positional_index.json', model['index'])
    docs = list(model['documents'])
    for matrix in ('raw_tf', 'weighted_tf', 'tfidf', 'normalized'):
        rows = [[term] + [values[doc] for doc in docs] for term, values in model[matrix].items()]
        write_csv(output / (matrix + '.csv'), ['term'] + docs, rows)
    write_csv(output / 'df_idf.csv', ['term', 'df', 'idf'],
              [[term, model['df'][term], model['idf'][term]] for term in model['index']])
    write_csv(output / 'document_lengths.csv', ['document', 'length'], model['lengths'].items())
    queries = [dict(label=p['label'], **search(model, p['phrase'], p['mode'], p['other'])) for p in presets]
    write_json(output / 'phrase_queries.json', queries[:2])
    write_json(output / 'boolean_queries.json', queries[2:])
    rows = [[q['label'], r['document'], r['similarity']] for q in queries for r in q['results']]
    write_csv(output / 'similarities.csv', ['query', 'document', 'similarity'], rows)
    rows = [[q['label'], r['rank'], r['document'], r['similarity']] for q in queries for r in q['results']]
    write_csv(output / 'rankings.csv', ['query', 'rank', 'document', 'similarity'], rows)
