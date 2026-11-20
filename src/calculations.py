"""Part B: full-precision TF-IDF and L2 normalization. No reference scores live here."""

import math
from collections import Counter


# Member 2: Weight a term count.
def weighted_tf(frequency):
    """Turn an occurrence count into 1 + log10(TF); absent terms have weight zero."""
    return 1 + math.log10(frequency) if frequency > 0 else 0.0


# Members 2 and 3: Calculate term counts and document weights.
def calculate_collection(index, documents):
    """Derive every matrix from Spark positions, using terms as rows and docs as columns.

    Return raw/weighted TF, DF/IDF, TF-IDF, document norms, and normalized weights.
    Keep floats unrounded: four-decimal formatting belongs only in the interface.
    """
    term_counts = {}
    weighted_counts = {}
    document_frequency = {}
    inverse_document_frequency = {}
    tfidf_weights = {}

    # Member 2: Count positions per document and documents per term.
    for term, positions_by_document in index.items():
        term_counts[term] = {
            document_id: len(positions_by_document.get(document_id, []))
            for document_id in documents
        }
        weighted_counts[term] = {
            document_id: weighted_tf(count) for document_id, count in term_counts[term].items()
        }
        document_frequency[term] = len(positions_by_document)
        inverse_document_frequency[term] = math.log10(len(documents) / document_frequency[term])
        # Member 3: Calculate the TF-IDF row for this term.
        tfidf_weights[term] = {
            document_id: weighted_count * inverse_document_frequency[term]
            for document_id, weighted_count in weighted_counts[term].items()
        }

    # Member 3: Find document lengths and normalize the vectors.
    document_lengths = {}
    for document_id in documents:
        sum_of_squares = sum(tfidf_weights[term][document_id] ** 2 for term in index)
        document_lengths[document_id] = math.sqrt(sum_of_squares)

    normalized_weights = {}
    for term in index:
        normalized_weights[term] = {}
        for document_id in documents:
            length = document_lengths[document_id]
            weight = tfidf_weights[term][document_id]
            normalized_weights[term][document_id] = weight / length if length else 0.0

    return dict(raw_tf=term_counts, weighted_tf=weighted_counts, df=document_frequency,
                idf=inverse_document_frequency, tfidf=tfidf_weights,
                lengths=document_lengths, normalized=normalized_weights)


# Member 5: Build the query vector for scoring.
def query_vector(tokens, collection_idf):
    """Use the collection IDF to weight the query terms, then normalize their weights."""
    term_weights = []
    for term, query_count in Counter(tokens).items():
        weighted_count = weighted_tf(query_count)
        term_idf = collection_idf.get(term, 0.0)
        term_weights.append(dict(term=term, tf=query_count, weighted_tf=weighted_count,
                                 idf=term_idf, tfidf=weighted_count * term_idf))
    query_length = math.sqrt(sum(term_weight['tfidf'] ** 2 for term_weight in term_weights))
    for term_weight in term_weights:
        term_weight['normalized'] = term_weight['tfidf'] / query_length if query_length else 0.0
    return dict(tokens=tokens, rows=term_weights, length=query_length)
