"""Build an import in isolation before publishing it to the web interface."""

import re
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from src.calculations import calculate_collection
from src.exports import export_all, EXPORT_FILES
from src.indexing import document_number, index_documents
from src.queries import PRESETS


def suggested_queries(documents):
    phrase_counts = Counter()
    word_counts = Counter()
    for text in documents.values():
        tokens = text.lower().split()
        word_counts.update(token for token in tokens if len(token) <= 300)
        phrase_counts.update(
            first_word + ' ' + next_word for first_word, next_word in zip(tokens, tokens[1:])
            if len(first_word) + len(next_word) < 300
        )
    if 'machine learning' in phrase_counts and 'data science' in phrase_counts:
        return PRESETS
    phrases = [term for term, _ in phrase_counts.most_common(2)]
    phrases += [term for term, _ in word_counts.most_common(2) if term not in phrases]
    presets = [dict(label=phrase, phrase=phrase, other='', mode='phrase') for phrase in phrases[:2]]
    if len(presets) == 2:
        first_phrase, second_phrase = phrases[:2]
        for mode, label in [('and', 'AND'), ('and_not', 'AND NOT')]:
            presets.append(dict(label=f'{first_phrase} {label} {second_phrase}',
                                phrase=first_phrase, other=second_phrase, mode=mode))
    return presets


def read_uploads(files):
    if not 1 <= len(files) <= 80:
        raise ValueError('Choose between 1 and 80 text files.')
    names = [Path((upload.filename or '').replace('\\', '/')).name for upload in files]
    reserved_ids = {Path(name).stem for name in names if re.fullmatch(r'd[1-9]\d{0,8}\.txt', name)}
    documents, filenames_by_id = {}, {}
    next_number = 1
    vocabulary = set()
    for name, upload in zip(names, files):
        if not name.lower().endswith('.txt'):
            raise ValueError('Choose .txt files only.')
        try:
            text = upload.read().decode('utf-8-sig').strip()
        except UnicodeDecodeError:
            raise ValueError(f'{name} must be a UTF-8 text file.') from None
        if not text or '\x00' in text:
            raise ValueError(f'{name} must contain plain text.')
        vocabulary.update(text.lower().split())
        if len(vocabulary) * len(files) > 100000:
            raise ValueError('This selection is too large for the interactive matrices. Choose fewer files.')
        document_id = Path(name).stem
        if document_id not in reserved_ids or document_id in documents:
            while f'd{next_number}' in reserved_ids or f'd{next_number}' in documents:
                next_number += 1
            document_id = f'd{next_number}'
        documents[document_id] = text
        filenames_by_id[document_id] = name
    ordered_documents = {doc_id: documents[doc_id] for doc_id in sorted(documents, key=document_number)}
    return ordered_documents, filenames_by_id


# Member 1: Pass the Spark index and document weights to the search app.
def process_documents(documents, labels):
    positional_index, spark_version = index_documents(documents)
    presets = suggested_queries(documents)
    model = dict(documents=documents, filenames=labels, index=positional_index,
                 metadata=dict(engine='Apache Spark / PySpark', spark_version=spark_version),
                 **calculate_collection(positional_index, documents))
    with TemporaryDirectory() as directory:
        export_all(model, directory, presets)
        exports = {name: (Path(directory) / name).read_bytes() for name in EXPORT_FILES}
    return model, presets, exports
