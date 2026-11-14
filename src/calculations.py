"""Part B: full-precision TF-IDF and L2 normalization. No reference scores live here."""

import math
from collections import Counter


def weighted_tf(frequency):
    """Turn an occurrence count into 1 + log10(TF); absent terms have weight zero."""
    return 1 + math.log10(frequency) if frequency > 0 else 0.0


def calculate_collection(index, documents):
    """Derive every matrix from Spark positions, using terms as rows and docs as columns.

    Return raw/weighted TF, DF/IDF, TF-IDF, document norms, and normalized weights.
    Keep floats unrounded: four-decimal formatting belongs only in the interface.
    """
    raw_tf, weighted, df, idf, tfidf = {}, {}, {}, {}, {}
    for term, postings in index.items():
        raw_tf[term] = {doc: len(postings.get(doc, [])) for doc in documents}
        weighted[term] = {doc: weighted_tf(raw_tf[term][doc]) for doc in documents}
        df[term] = len(postings)
        idf[term] = math.log10(len(documents) / df[term])
        tfidf[term] = {doc: weighted[term][doc] * idf[term] for doc in documents}

    lengths = {}
    for doc in documents:
        lengths[doc] = math.sqrt(sum(tfidf[term][doc] ** 2 for term in index))
    normalized = {}
    for term in index:
        normalized[term] = {}
        for doc in documents:
            normalized[term][doc] = tfidf[term][doc] / lengths[doc] if lengths[doc] else 0.0
    return dict(raw_tf=raw_tf, weighted_tf=weighted, df=df, idf=idf,
                tfidf=tfidf, lengths=lengths, normalized=normalized)


def query_vector(tokens, collection_idf):
    """Weight query counts with existing collection IDF, then L2-normalize.

    Unknown terms are reported with zero weight because they have no collection
    dimension. Phrase matching still rejects a phrase containing any unknown term.
    """
    rows = []
    for term, count in Counter(tokens).items():
        weight = weighted_tf(count)
        idf = collection_idf.get(term, 0.0)
        rows.append(dict(term=term, tf=count, weighted_tf=weight, idf=idf, tfidf=weight * idf))
    length = math.sqrt(sum(row['tfidf'] ** 2 for row in rows))
    for row in rows:
        row['normalized'] = row['tfidf'] / length if length else 0.0
    return dict(tokens=tokens, rows=rows, length=length)
