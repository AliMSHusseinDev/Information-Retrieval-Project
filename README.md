# Information Retrieval Project

Import text documents to build a searchable collection. Spark records where each word appears. The search engine uses those positions to find exact phrases, then uses TF-IDF and cosine similarity to rank the matching documents. You can explore the calculations and export the results as CSV or JSON.

## How to run

Double-click `Launch_IR.bat`.

## Calculation rules

The same rules apply to every import. `N` is the number of selected documents. Importing all ten files from one supplied category gives `N = 10`.

| Step | Rule |
| --- | --- |
| Tokenization | Convert text to lowercase and split it on whitespace. Punctuation stays attached to its token. The supplied documents contain no punctuation. |
| Word positions | Count every token from left to right, starting at 1 in each document. An exact phrase matches when its tokens occupy consecutive positions in order. |
| Term frequency (TF) | Count how many times a term occurs in the document. For a query vector, count its occurrences in the query. |
| Document frequency (DF) | Count how many selected documents contain the term. Each document contributes at most once. |
| Inverse document frequency (IDF) | Use the base-10 logarithm: `IDF = log₁₀(N / DF)`. A term present in every document has IDF zero. |
| Weighted TF | Use `1 + log₁₀(TF)` when TF is positive. An absent term has weight zero. |
| TF-IDF | Multiply weighted TF by the term’s collection IDF. Query terms use the same collection IDF. |
| L2 normalization | For each document and query vector, calculate its length as the square root of the sum of its squared TF-IDF weights. Divide each weight by that length. A zero-length vector stays zero. |
| Cosine similarity | Multiply the normalized query and document weights for each term, then sum the products. Rank matching documents from highest score to lowest. |

