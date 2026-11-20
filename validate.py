"""Focused unittest validation against the supplied PDF; exits nonzero on failure.

Run with python validate.py. Test downloads and reference files use temporary directories.
The HTTP checks import the Technology collection through the live Spark pipeline.
"""
import base64
import csv
import io
import json
import math
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from app import create_app
from run_spark import build_reference
from src.calculations import calculate_collection, query_vector
from src.indexing import read_documents
from src.queries import PRESETS, phrase_matches, search
from src.storage import load_model
from src.exports import EXPORT_FILES
from tests.reference import DOCUMENTS, POSTINGS, LENGTHS, NORMALIZED, PHRASES, RANKINGS, QUERY_LENGTHS

ROOT = Path(__file__).resolve().parent


class TechnologyValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.reference_dir = Path(temp.name) / 'reference'
        cls.output_dir = Path(temp.name) / 'outputs'
        build_reference(ROOT, cls.reference_dir)
        cls.model = load_model(ROOT, cls.reference_dir)
        cls.client = create_app(output_dir=cls.output_dir).test_client()
        files = sorted((ROOT / 'data' / 'Main' / '2. Technology').glob('*.txt'))
        response = cls.client.post('/api/import', data={
            'documents': [(io.BytesIO(file.read_bytes()), file.name) for file in files]})
        if response.status_code != 200:
            raise AssertionError(response.get_json())
        cls.base = response.json['url']
        cls.reference_index = {}
        for term, postings in POSTINGS.items():
            cls.reference_index[term] = {}
            for posting in postings.split():
                doc, positions = posting.split(':')
                cls.reference_index[term][doc] = [int(value) for value in positions.split(',')]

    def test_01_original_dataset_and_spark_provenance(self):
        expected = {f'd{i}': text for i, text in enumerate(DOCUMENTS, 1)}
        self.assertEqual(read_documents(ROOT / 'data' / 'Main' / '2. Technology'), expected)
        self.assertEqual(self.model['documents'], expected)
        self.assertEqual(len(self.model['index']), 27)
        self.assertEqual(sum(len(text.split()) for text in expected.values()), 64)
        self.assertEqual(self.model['metadata']['engine'], 'Apache Spark / PySpark')
        self.assertEqual(self.model['metadata']['spark_version'], '4.0.1')

    def test_02_complete_positional_index(self):
        self.assertEqual(self.model['index'], self.reference_index)
        self.assertEqual(list(self.model['index']), sorted(POSTINGS))
        for postings in self.model['index'].values():
            self.assertEqual(list(postings), sorted(postings, key=lambda doc: int(doc[1:])))

    def test_03_all_matrix_cells_and_document_norms(self):
        # Independent formula evaluation from the PDF posting fixture, not app helpers.
        for term, postings in self.reference_index.items():
            idf = math.log10(10 / len(postings))
            self.assertEqual(self.model['df'][term], len(postings))
            self.assertAlmostEqual(self.model['idf'][term], idf, places=14)
            for doc in self.model['documents']:
                tf = len(postings.get(doc, []))
                weighted = 1 + math.log10(tf) if tf else 0
                self.assertEqual(self.model['raw_tf'][term][doc], tf)
                self.assertAlmostEqual(self.model['weighted_tf'][term][doc], weighted, places=14)
                self.assertAlmostEqual(self.model['tfidf'][term][doc], weighted * idf, places=14)
        for doc, expected in zip(self.model['documents'], LENGTHS):
            self.assertAlmostEqual(self.model['lengths'][doc], expected, delta=.00005)
            self.assertAlmostEqual(sum(row[doc] ** 2 for row in self.model['normalized'].values()), 1, places=13)

    def test_04_complete_pdf_normalized_table(self):
        for term in self.reference_index:
            expected = dict(pair.split(':') for pair in NORMALIZED[term].split())
            for doc in self.model['documents']:
                with self.subTest(term=term, doc=doc):
                    self.assertAlmostEqual(self.model['normalized'][term][doc], float(expected.get(doc, 0)), delta=.00005)

    def test_05_exact_phrase_positions_and_ranges(self):
        for phrase, expected in zip(['machine learning', 'data science'], PHRASES):
            actual = phrase_matches(self.model['index'], phrase.split())
            self.assertEqual({doc: match['starts'] for doc, match in actual.items()}, expected)
            self.assertEqual({doc: match['ranges'] for doc, match in actual.items()},
                             {doc: [[p, p + 1] for p in starts] for doc, starts in expected.items()})

    def test_06_all_four_pdf_queries(self):
        for preset, expected, length in zip(PRESETS, RANKINGS, QUERY_LENGTHS):
            with self.subTest(query=preset['label']):
                result = search(self.model, preset['phrase'], preset['mode'], preset['other'])
                self.assertEqual([row['document'] for row in result['results']], [doc for doc, score in expected])
                self.assertAlmostEqual(result['query']['length'], length, delta=.0000005)
                for row, (doc, score) in zip(result['results'], expected):
                    self.assertAlmostEqual(row['similarity'], score, delta=.00005)
                    self.assertAlmostEqual(sum(part['product'] for part in row['contributions']), row['similarity'], places=14)
        negative = search(self.model, 'machine learning', 'and_not', 'data science')
        self.assertEqual(negative['query']['tokens'], ['machine', 'learning'])
        self.assertEqual(set(row['document'] for row in negative['results']), {'d1', 'd2', 'd7', 'd10'})

    def test_07_edge_cases_and_repeated_terms(self):
        index = self.model['index']
        self.assertEqual(phrase_matches(index, ['learning', 'machine'])['d5']['starts'], [2])
        self.assertEqual(phrase_matches(index, ['machine', 'machine']), {})
        self.assertEqual(phrase_matches(index, ['and']), {'d5': {'starts': [8], 'ranges': [[8, 8]]}})
        self.assertEqual(search(self.model, '  MACHINE   learning  ')['count'], 5)
        self.assertEqual(search(self.model, 'unknown')['count'], 0)
        self.assertEqual(search(self.model, 'machine', 'and', 'unknown')['count'], 0)
        self.assertEqual(search(self.model, 'machine learning', 'and_not', 'unknown')['count'], 5)
        self.assertEqual(search(self.model, 'machine learning', 'and_not', 'machine learning')['count'], 0)
        vector = query_vector(['machine', 'machine', 'learning'], self.model['idf'])
        self.assertEqual(vector['rows'][0]['tf'], 2)
        self.assertAlmostEqual(vector['rows'][0]['weighted_tf'], 1 + math.log10(2))
        self.assertEqual(query_vector(['missing'], {})['length'], 0)
        zero = calculate_collection({'common': {'d1': [1], 'd2': [1]}}, {'d1': 'common', 'd2': 'common'})
        self.assertEqual(zero['normalized']['common'], {'d1': 0, 'd2': 0})

    def test_08_gui_routes_and_live_api(self):
        for route in ['/', '/index', '/analytics', '/search', '/mathematics', '/reports']:
            response = self.client.get(self.base + route.lstrip("/"))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'IR Project', response.data)
        imported = self.client.get(self.base + 'api/model').json['model']
        for key in self.model.keys() - {'metadata'}:
            self.assertEqual(imported[key], self.model[key])
        self.assertEqual(self.client.get(self.base + 'api/index?term=machine').json, self.reference_index['machine'])
        for preset, expected in zip(PRESETS, RANKINGS):
            result = self.client.post(self.base + 'api/search', json=preset)
            self.assertEqual(result.status_code, 200)
            self.assertEqual([row['document'] for row in result.json['results']], [doc for doc, _ in expected])

    def test_09_invalid_requests_and_paths(self):
        for payload in [None, [], {}, {'phrase': []}, {'phrase': ''}, {'phrase': 'x' * 301},
                        {'phrase': 'machine', 'mode': 'invalid'}, {'phrase': 'machine', 'mode': 'and'},
                        {'phrase': 'machine', 'mode': 'and_not', 'other': 42}]:
            self.assertEqual(self.client.post(self.base + 'api/search', json=payload).status_code, 400)
        self.assertEqual(self.client.get(self.base + 'download/not-allowed.txt').status_code, 404)
        self.assertEqual(self.client.get(self.base + 'download/../app.py').status_code, 404)
        self.assertEqual(self.client.get(self.base + 'missing').status_code, 404)
        self.assertEqual(self.client.post(self.base + 'api/search', json={'phrase': '<script>alert(1)</script>'}).json['count'], 0)

    def test_10_exported_matrices_and_queries(self):
        self.assertTrue(all(row['ready'] for row in self.client.get(self.base + 'api/exports').json))
        self.assertEqual(json.loads((self.reference_dir / 'positional_index.json').read_text()), self.reference_index)
        for name in ['raw_tf', 'weighted_tf', 'tfidf', 'normalized']:
            with (self.reference_dir / (name + '.csv')).open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 27)
            for row in rows:
                for doc in self.model['documents']:
                    self.assertEqual(float(row[doc]), self.model[name][row['term']][doc])
        for filename, chosen in [('phrase_queries.json', PRESETS[:2]), ('boolean_queries.json', PRESETS[2:])]:
            values = json.loads((self.reference_dir / filename).read_text())
            for stored, preset in zip(values, chosen):
                self.assertEqual(stored, dict(label=preset['label'], **search(self.model, preset['phrase'], preset['mode'], preset['other'])))
        self.assertEqual(list(self.output_dir.iterdir()), [])
        self.assertEqual(self.client.get(self.base + 'reports').status_code, 200)
        self.assertEqual(self.client.head(self.base + 'download/raw_tf.csv').status_code, 200)
        self.assertEqual(list(self.output_dir.iterdir()), [])
        downloaded = set()
        for name in EXPORT_FILES:
            response = self.client.get(self.base + 'download/' + name)
            self.assertEqual(response.status_code, 200)
            downloaded.add(name)
            self.assertEqual({p.name for p in self.output_dir.iterdir()}, downloaded)
            self.assertEqual((self.output_dir / name).read_bytes(), response.data)
            if name == 'model.json':
                self.assertEqual(response.json, self.client.get(self.base + 'api/model').json['model'])
            else:
                self.assertEqual(response.data, (self.reference_dir / name).read_bytes())
            response.close()
        response = self.client.get(self.base + 'download/all.zip')
        self.assertEqual((self.output_dir / 'ir-results.zip').read_bytes(), response.data)
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(set(archive.namelist()), set(EXPORT_FILES))
            for name in EXPORT_FILES:
                self.assertEqual(archive.read(name), self.client.get(self.base + 'download/' + name).data)
        response.close()

    def test_11_empty_start_and_atomic_replacement(self):
        for route in ('/api/model', '/api/index', '/api/exports', '/download/all.zip'):
            self.assertEqual(self.client.get(route).status_code, 409)
        self.assertFalse(self.client.get('/api/health').json['loaded'])
        self.assertIn(b'Import Documents', self.client.get('/').data)
        for contents, name in [(b'', 'empty.txt'), (b'hello', 'wrong.csv'), (b'\xff', 'bad.txt')]:
            response = self.client.post(self.base + 'api/import',
                                        data={'documents': (io.BytesIO(contents), name)})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(self.base + 'api/index').json, self.reference_index)

    def test_12_offline_reference_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError):
                load_model(root)
            shutil.copytree(ROOT / 'data', root / 'data')
            shutil.copytree(self.reference_dir, root / 'artifacts' / 'technology')
            (root / 'data' / 'Main' / '2. Technology' / 'd1.txt').write_text('changed')
            with self.assertRaises(RuntimeError):
                load_model(root)

    def test_13_restart_keeps_prior_downloads_outside_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = Path(tmp) / 'outputs'
            create_app(output_dir=outputs)
            (outputs / 'raw_tf.csv').write_bytes(b'previous export')
            create_app(output_dir=outputs)
            self.assertEqual(list(outputs.iterdir()), [])
            archived, = (Path(tmp) / 'previous_exports').glob('*/raw_tf.csv')
            self.assertEqual(archived.read_bytes(), b'previous export')

    def test_14_screenshots_are_unique_and_survive_restart(self):
        folder = self.output_dir.parent / 'screenshots'
        self.assertEqual(list(folder.iterdir()), [])
        payload = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPgEpEDAABoAD1UCKP3AAAAAElFTkSuQmCC')
        files = []
        for _ in range(2):
            response = self.client.post(self.base + 'api/screenshots/analytics?label=TF-IDF',
                                        data=payload, content_type='image/png')
            self.assertEqual(response.status_code, 201)
            files.append(folder / response.json['name'])
        truncated = self.client.post(self.base + 'api/screenshots/analytics',
                                     data=payload[:-1], content_type='image/png')
        self.assertEqual(truncated.status_code, 400)
        self.assertEqual(set(folder.iterdir()), set(files))
        self.assertNotEqual(*files)
        create_app(output_dir=self.output_dir)
        for path in files:
            self.assertEqual(path.suffix, '.png')
            self.assertEqual(path.read_bytes(), payload)


if __name__ == '__main__':
    unittest.main(verbosity=2)
