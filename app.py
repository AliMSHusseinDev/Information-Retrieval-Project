"""Thin Flask routes. All retrieval mathematics lives in src/, independently of HTTP."""

import io
import secrets
import sys
from collections import OrderedDict
from threading import Lock
import zipfile
from pathlib import Path
from flask import make_response, Flask, jsonify, render_template, request, send_file, abort, Blueprint, g
from src.exports import prepare_downloads, save_download
from src.calculations import query_vector
from src.screenshots import save_screenshot
from src.queries import search
from src.imports import process_documents, read_uploads, searchable_pairs

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
PAGES = {
    'dashboard': ('Overview', 'A clear view of your collection, from tokens to rankings.'),
    'index': ('Positional index', 'Every term. Every occurrence. In exactly the right place.'),
    'analytics': ('TF-IDF analytics', 'Explore the numbers that make retrieval meaningful.'),
    'search': ('Search engine', 'Find exact phrases. Explore the relevance behind every result.'),
    'mathematics': ('Query mathematics', 'Follow a query from its first token to its final score.'),
    'reports': ('Export & report', 'Real calculations, ready for your next discussion.'),
}


def create_app(root=ROOT, *, output_dir=None):
    if output_dir is None:
        project = Path(sys.executable).parent if getattr(sys, 'frozen', False) else root
        output_dir = project / 'outputs'
    screenshot_dir = Path(output_dir).parent / 'screenshots'
    screenshot_dir.mkdir(exist_ok=True, parents=True)
    prepare_downloads(output_dir)
    app = Flask(__name__, template_folder=str(root / 'templates'), static_folder=str(root / 'static'))
    app.json.sort_keys = False
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    views = Blueprint('collection', __name__)
    collections = OrderedDict()
    access = Lock()
    processing = Lock()

    @views.url_value_preprocessor
    def select_collection(endpoint, values):
        key = values.pop('key', None)
        with access:
            g.collection = collections.get(key)
            if g.collection:
                collections.move_to_end(key)
        g.key = key

    @views.before_request
    def require_collection():
        if not g.collection and request.endpoint.rsplit('.', 1)[-1] not in ('page_view', 'health', 'import_files'):
            return jsonify(error='Import documents to open a collection.'), 409

    @views.post('/api/import')
    def import_files():
        try:
            documents, names = read_uploads(request.files.getlist('documents'))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        if not processing.acquire(blocking=False):
            return jsonify(error='An import is running. Try again when it finishes.'), 409
        try:
            collection = process_documents(documents, names)
            key = secrets.token_urlsafe(20)
            with access:
                collections[key] = collection
                collections.pop(g.key, None)
                if len(collections) > 4:
                    collections.popitem(last=False)
            return jsonify(url=f'/c/{key}/')
        except Exception:
            app.logger.exception('Spark import failed')
            return jsonify(error='Spark could not finish the import. Check the launcher console and retry.'), 500
        finally:
            processing.release()

    @app.errorhandler(413)
    def too_large(error):
        if request.endpoint and request.endpoint.endswith('.capture'):
            return jsonify(error='The screenshot is too large to save (48 MB limit).'), 413
        return jsonify(error='Choose a smaller batch (under 2 MB per import).'), 413

    @app.after_request
    def response_headers(response):
        if request.endpoint == 'active.model_data' and response.status_code == 200:
            response.cache_control.private = True
            response.cache_control.max_age = 600
        elif request.endpoint != 'static':
            response.cache_control.no_store = True
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        return response

    @views.get('/')
    @views.get('/<page>')
    def page_view(page='dashboard'):
        if page not in PAGES:
            abort(404)
        prefix = f'/c/{g.key}/' if g.collection else '/'
        phrase = ''
        cards = []
        selected_index = None
        if page == 'dashboard' and g.collection:
            model = g.collection[0]
            phrases = list(dict.fromkeys(
                pair for text in model['documents'].values()
                for pair in searchable_pairs(text.lower().split())
            ))
            if phrases:
                previous = request.cookies.get('last_preview', type=int)
                if len(phrases) > 1 and previous is not None and 0 <= previous < len(phrases):
                    selected_index = (previous + 1 + secrets.randbelow(len(phrases) - 1)) % len(phrases)
                else:
                    selected_index = secrets.randbelow(len(phrases))
                phrase = phrases[selected_index]
                tokens = phrase.split()
                weights = {row['term']: row['tfidf'] for row in query_vector(tokens, model['idf'])['rows']}
                cards = [(term, weights[term]) for term in tokens]
        response = make_response(render_template(
            (page if g.collection else 'empty') + '.html', page=page, pages=PAGES,
            title=PAGES[page][0], description=PAGES[page][1], loaded=bool(g.collection),
            prefix=prefix, preview_phrase=phrase, preview_cards=cards,
        ))
        if selected_index is not None:
            response.set_cookie('last_preview', str(selected_index), path=prefix, httponly=True, samesite='Lax')
        return response

    @views.get('/api/model')
    def model_data():
        model, presets, _ = g.collection
        return jsonify(model=model, presets=presets)

    @views.get('/api/health')
    def health():
        return jsonify(application='lumen-ir', loaded=bool(g.collection))

    @views.get('/api/index')
    def index_data():
        model = g.collection[0]
        term = request.args.get('term', '').lower().strip()
        return jsonify(model['index'].get(term, {}) if term else model['index'])

    @views.post('/api/search')
    def search_data():
        model = g.collection[0]
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error='Send a JSON object containing a phrase and mode.'), 400
        try:
            return jsonify(search(model, body.get('phrase'), body.get('mode', 'phrase'), body.get('other', '')))
        except (ValueError, TypeError):
            # Validation errors are expected user input, not server tracebacks.
            return jsonify(error='Enter a phrase (up to 300 characters / 40 tokens) and a valid search mode. Boolean modes require two phrases.'), 400

    @views.post('/api/screenshots/<page>')
    def capture(page):
        if page not in PAGES or page == 'reports':
            abort(404)
        request.max_content_length = 48 * 1024 * 1024
        try:
            name = save_screenshot(screenshot_dir, root / 'static', page, request.get_json())
        except ValueError as error:
            return jsonify(error=str(error)), 400
        except OSError:
            app.logger.exception('Could not save screenshot')
            return jsonify(error='Could not write to the screenshots folder.'), 500
        return jsonify(name=name), 201

    @views.get('/api/exports')
    def export_status():
        return jsonify([dict(name=name, ready=True, bytes=len(data))
                        for name, data in g.collection[2].items()])

    @views.get('/download/<name>')
    def download(name):
        exports = g.collection[2]
        if name == 'all.zip':
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                for filename, data in exports.items():
                    archive.writestr(filename, data)
            name = 'ir-results.zip'
            data = buffer.getvalue()
        elif name in exports:
            data = exports[name]
        else:
            abort(404)
        if request.method == 'GET':
            try:
                save_download(output_dir, name, data)
            except OSError:
                app.logger.exception('Could not save export %s', name)
                return jsonify(error='Could not save the file in outputs. Close any open copy and check folder permissions.'), 500
        return send_file(io.BytesIO(data), as_attachment=True, download_name=name)

    app.register_blueprint(views)
    app.register_blueprint(views, url_prefix='/c/<key>', name='active')
    return app


if __name__ == '__main__':
    from waitress import serve
    print('Technology IR is available at http://127.0.0.1:5000 — Ctrl+C to close.')
    serve(create_app(), host='127.0.0.1', port=5000)
