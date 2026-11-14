"""Exact positional phrases, phrase-set Boolean filtering, and cosine ranking."""

from src.calculations import query_vector
from src.indexing import document_number

PRESETS = [
    dict(label='machine learning', mode='phrase', phrase='machine learning', other=''),
    dict(label='data science', mode='phrase', phrase='data science', other=''),
    dict(label='machine learning AND data science', mode='and', phrase='machine learning', other='data science'),
    dict(label='machine learning AND NOT data science', mode='and_not', phrase='machine learning', other='data science'),
]


def phrase_matches(index, tokens):
    """Find start positions where every token occurs at start + its token offset.

    Input: an index and lowercase tokens. Output: doc -> all starts and ranges.
    This uses position lists, never document substring matching.
    """
    if not tokens or any(term not in index for term in tokens):
        return {}
    candidates = set(index[tokens[0]])
    for term in tokens[1:]:
        candidates.intersection_update(index[term])
    matches = {}
    for doc in sorted(candidates, key=document_number):
        starts = set(index[tokens[0]][doc])
        for offset, term in enumerate(tokens[1:], start=1):
            starts.intersection_update(position - offset for position in index[term][doc])
        if starts:
            positions = sorted(starts)
            matches[doc] = dict(starts=positions, ranges=[[p, p + len(tokens) - 1] for p in positions])
    return matches


def clean_phrase(value, label):
    """Validate a short whitespace-tokenized phrase supplied through the API."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty phrase.')
    if len(value) > 300 or len(value.split()) > 40:
        raise ValueError(f'{label} is too long (maximum 300 characters / 40 tokens).')
    return value.lower().split()


def search(model, phrase, mode='phrase', other=''):
    """Filter exact phrase matches, construct a positive query vector, and rank.

    AND includes both phrases in query weighting. AND NOT uses the second phrase
    only as a filter and never changes original normalized document vectors.
    Return matches, query mathematics, and per-term dot-product contributions.
    """
    if mode not in ('phrase', 'and', 'and_not'):
        raise ValueError('Choose phrase, and, or and_not mode.')
    tokens = clean_phrase(phrase, 'First phrase')
    other_tokens = clean_phrase(other, 'Second phrase') if mode != 'phrase' else []
    first = phrase_matches(model['index'], tokens)
    second = phrase_matches(model['index'], other_tokens)
    candidates = set(first)
    if mode == 'and':
        candidates.intersection_update(second)
    elif mode == 'and_not':
        candidates.difference_update(second)
    positive_tokens = tokens + other_tokens if mode == 'and' else tokens
    vector = query_vector(positive_tokens, model['idf'])
    results = []
    for doc in candidates:
        contributions = []
        for row in vector['rows']:
            doc_weight = model['normalized'].get(row['term'], {}).get(doc, 0.0)
            contributions.append(dict(term=row['term'], query_weight=row['normalized'],
                                      document_weight=doc_weight, product=row['normalized'] * doc_weight))
        results.append(dict(document=doc, text=model['documents'][doc], first=first[doc],
                            second=second.get(doc), contributions=contributions,
                            similarity=sum(row['product'] for row in contributions)))
    results.sort(key=lambda row: (-row['similarity'], document_number(row['document'])))
    for rank, row in enumerate(results, start=1):
        row['rank'] = rank
    unknown = sorted(set(tokens + other_tokens) - set(model['index']))
    return dict(phrase=' '.join(tokens), other=' '.join(other_tokens), mode=mode, query=vector,
                first_matches=first, second_matches=second, unknown_terms=unknown,
                results=results, count=len(results))
