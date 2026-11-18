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
    pairs = Counter()
    words = Counter()
    for text in documents.values():
        tokens = text.lower().split()
        words.update(token for token in tokens if len(token) <= 300)
        pairs.update(a + ' ' + b for a, b in zip(tokens, tokens[1:]) if len(a) + len(b) < 300)
    if 'machine learning' in pairs and 'data science' in pairs:
        return PRESETS
    phrases = [term for term, _ in pairs.most_common(2)]
    phrases += [term for term, _ in words.most_common(2) if term not in phrases]
    presets = [dict(label=p, phrase=p, other='', mode='phrase') for p in phrases[:2]]
    if len(presets) == 2:
        a, b = phrases[:2]
        for mode, label in [('and', 'AND'), ('and_not', 'AND NOT')]:
            presets.append(dict(label=f'{a} {label} {b}', phrase=a, other=b, mode=mode))
    return presets


def read_uploads(files):
    if not 1 <= len(files) <= 80:
        raise ValueError('Choose between 1 and 80 text files.')
    names = [Path((f.filename or '').replace('\\', '/')).name for f in files]
    reserved = {Path(name).stem for name in names if re.fullmatch(r'd[1-9]\d{0,8}\.txt', name)}
    documents, labels = {}, {}
    sequence = 1
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
        doc = Path(name).stem
        if doc not in reserved or doc in documents:
            while f'd{sequence}' in reserved or f'd{sequence}' in documents:
                sequence += 1
            doc = f'd{sequence}'
        documents[doc] = text
        labels[doc] = name
    return dict(sorted(documents.items(), key=lambda item: document_number(item[0]))), labels


def process_documents(documents, labels):
    index, version = index_documents(documents)
    presets = suggested_queries(documents)
    model = dict(documents=documents, filenames=labels, index=index,
                 metadata=dict(engine='Apache Spark / PySpark', spark_version=version),
                 **calculate_collection(index, documents))
    with TemporaryDirectory() as directory:
        export_all(model, directory, presets)
        exports = {name: (Path(directory) / name).read_bytes() for name in EXPORT_FILES}
    return model, presets, exports
