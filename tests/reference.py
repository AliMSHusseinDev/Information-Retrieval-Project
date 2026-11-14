"""Independent Technology reference fixtures transcribed from PDF pages 3–7.

Constants belong in tests only, never in the production calculation pipeline.
"""
DOCUMENTS = [
    'machine learning',
    'machine learning improves data processing',
    'data science tools support analysis',
    'artificial intelligence powers smart systems',
    'machine learning machine models support data science and machine learning',
    'cloud computing supports data storage',
    'artificial intelligence uses machine learning models',
    'data science explores data analytics through research computing systems',
    'cloud computing cloud storage supports data systems',
    'machine learning models improve machine learning applications research data systems',
]
# Every posting on page 3 (compact notation: doc:position,position).
POSTINGS = {
    'analysis': 'd3:5', 'analytics': 'd8:5', 'and': 'd5:8', 'applications': 'd10:7',
    'artificial': 'd4:1 d7:1', 'cloud': 'd6:1 d9:1,3', 'computing': 'd6:2 d8:8 d9:2',
    'data': 'd2:4 d3:1 d5:6 d6:4 d8:1,4 d9:6 d10:9', 'explores': 'd8:3',
    'improve': 'd10:4', 'improves': 'd2:3', 'intelligence': 'd4:2 d7:2',
    'learning': 'd1:2 d2:2 d5:2,10 d7:5 d10:2,6',
    'machine': 'd1:1 d2:1 d5:1,3,9 d7:4 d10:1,5',
    'models': 'd5:4 d7:6 d10:3', 'powers': 'd4:3', 'processing': 'd2:5',
    'research': 'd8:7 d10:8', 'science': 'd3:2 d5:7 d8:2', 'smart': 'd4:4',
    'storage': 'd6:5 d9:4', 'support': 'd3:4 d5:5', 'supports': 'd6:3 d9:5',
    'systems': 'd4:5 d8:9 d9:7 d10:10', 'through': 'd8:6', 'tools': 'd3:3', 'uses': 'd7:3',
}
LENGTHS = [.4257, 1.4850, 1.6691, 1.7707, 1.5526, 1.3278, 1.5594, 2.0577, 1.5033, 1.8031]
# All nonzero normalized cells on page 5. Every omitted cell must be zero.
NORMALIZED = {
 'analysis': 'd3:.5991', 'analytics': 'd8:.4860', 'and': 'd5:.6441', 'applications': 'd10:.5546',
 'artificial': 'd4:.3947 d7:.4482', 'cloud': 'd6:.5264 d9:.6049',
 'computing': 'd6:.3938 d8:.2541 d9:.3478',
 'data': 'd2:.1043 d3:.0928 d5:.0998 d6:.1167 d8:.0979 d9:.1030 d10:.0859',
 'explores': 'd8:.4860', 'improve': 'd10:.5546', 'improves': 'd2:.6734',
 'intelligence': 'd4:.3947 d7:.4482',
 'learning': 'd1:.7071 d2:.2027 d5:.2523 d7:.1930 d10:.2172',
 'machine': 'd1:.7071 d2:.2027 d5:.2864 d7:.1930 d10:.2172',
 'models': 'd5:.3368 d7:.3353 d10:.2900', 'powers': 'd4:.5647', 'processing': 'd2:.6734',
 'research': 'd8:.3397 d10:.3877', 'science': 'd3:.3133 d5:.3368 d8:.2541',
 'smart': 'd4:.5647', 'storage': 'd6:.5264 d9:.4650', 'support': 'd3:.4188 d5:.4502',
 'supports': 'd6:.5264 d9:.4650', 'systems': 'd4:.2247 d8:.1934 d9:.2647 d10:.2207',
 'through': 'd8:.4860', 'tools': 'd3:.5991', 'uses': 'd7:.6413',
}
PHRASES = [
 {'d1': [1], 'd2': [1], 'd5': [1, 9], 'd7': [4], 'd10': [1, 5]},
 {'d3': [1], 'd5': [6], 'd8': [1]},
]
RANKINGS = [
 [('d1', 1.0000), ('d5', .3809), ('d10', .3072), ('d2', .2867), ('d7', .2730)],
 [('d5', .3513), ('d3', .3267), ('d8', .2715)], [('d5', .5113)],
 [('d1', 1.0000), ('d10', .3072), ('d2', .2867), ('d7', .2730)],
]
QUERY_LENGTHS = [.425721, .545341, .691834, .425721]
