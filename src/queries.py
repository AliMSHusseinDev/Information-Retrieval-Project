"""Exact positional phrases, phrase-set Boolean filtering, and cosine ranking."""

from src.calculations import query_vector
from src.indexing import document_number

PRESETS = [
    dict(label='machine learning', mode='phrase', phrase='machine learning', other=''),
    dict(label='data science', mode='phrase', phrase='data science', other=''),
    dict(label='machine learning AND data science', mode='and', phrase='machine learning', other='data science'),
    dict(label='machine learning AND NOT data science', mode='and_not', phrase='machine learning', other='data science'),
]


# Members 1 and 4: Match phrases using word positions.
def phrase_matches(index, tokens):
    """Find start positions where every token occurs at start + its token offset.

    Input: an index and lowercase tokens. Output: doc -> all starts and ranges.
    This uses position lists, never document substring matching.
    """
    if not tokens or any(term not in index for term in tokens):
        return {}
    candidate_document_ids = set(index[tokens[0]])
    for term in tokens[1:]:
        candidate_document_ids.intersection_update(index[term])

    phrase_locations = {}
    for document_id in sorted(candidate_document_ids, key=document_number):
        possible_starts = set(index[tokens[0]][document_id])
        for phrase_offset, term in enumerate(tokens[1:], start=1):
            term_positions = index[term][document_id]
            possible_starts.intersection_update(position - phrase_offset for position in term_positions)
        if possible_starts:
            start_positions = sorted(possible_starts)
            match_ranges = [[start, start + len(tokens) - 1] for start in start_positions]
            phrase_locations[document_id] = dict(starts=start_positions, ranges=match_ranges)
    return phrase_locations


# Member 4: Check and split a search phrase.
def clean_phrase(value, label):
    """Validate a short whitespace-tokenized phrase supplied through the API."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty phrase.')
    if len(value) > 300 or len(value.split()) > 40:
        raise ValueError(f'{label} is too long (maximum 300 characters / 40 tokens).')
    return value.lower().split()


# Members 1 and 5: Score the matching documents and put them in rank order.
def rank_documents(model, matching_ids, query_weights, first_matches, second_matches):
    ranked_results = []
    for document_id in matching_ids:
        term_contributions = []
        for query_term in query_weights['rows']:
            term = query_term['term']
            query_weight = query_term['normalized']
            document_weight = model['normalized'].get(term, {}).get(document_id, 0.0)
            term_contributions.append(dict(
                term=term, query_weight=query_weight, document_weight=document_weight,
                product=query_weight * document_weight
            ))
        similarity_score = sum(item['product'] for item in term_contributions)
        ranked_results.append(dict(
            document=document_id, text=model['documents'][document_id],
            first=first_matches[document_id], second=second_matches.get(document_id),
            contributions=term_contributions, similarity=similarity_score
        ))
    ranked_results.sort(key=lambda result: (-result['similarity'], document_number(result['document'])))
    for rank, result in enumerate(ranked_results, start=1):
        result['rank'] = rank
    return ranked_results


# Members 1 and 6: Retrieve matches and pass them to the ranking step.
def search(model, phrase, mode='phrase', other=''):
    """Find the exact phrases, apply the selected filter and rank its matches."""
    if mode not in ('phrase', 'and', 'and_not'):
        raise ValueError('Choose phrase, and, or and_not mode.')
    first_tokens = clean_phrase(phrase, 'First phrase')
    second_tokens = clean_phrase(other, 'Second phrase') if mode != 'phrase' else []
    first_matches = phrase_matches(model['index'], first_tokens)
    second_matches = phrase_matches(model['index'], second_tokens)

    matching_ids = set(first_matches)
    if mode == 'and':
        matching_ids.intersection_update(second_matches)
    elif mode == 'and_not':
        matching_ids.difference_update(second_matches)

    scoring_tokens = first_tokens + second_tokens if mode == 'and' else first_tokens
    query_weights = query_vector(scoring_tokens, model['idf'])
    ranked_results = rank_documents(model, matching_ids, query_weights, first_matches, second_matches)
    unknown_terms = sorted(set(first_tokens + second_tokens) - set(model['index']))
    return dict(phrase=' '.join(first_tokens), other=' '.join(second_tokens), mode=mode,
                query=query_weights, first_matches=first_matches, second_matches=second_matches,
                unknown_terms=unknown_terms, results=ranked_results, count=len(ranked_results))
