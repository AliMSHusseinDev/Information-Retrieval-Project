"""Thin Flask routes. All retrieval mathematics lives in src/, independently of HTTP."""

import io
import secrets
import sys
from collections import OrderedDict
from threading import Lock
import zipfile
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file, abort, Blueprint, g
from src.queries import search
from src.imports import process_documents, read_uploads

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
PAGES = {
    'dashboard': ('Overview', 'A clear view of your collection, from tokens to rankings.'),
    'index': ('Positional index', 'Every term. Every occurrence. In exactly the right place.'),
    'analytics': ('TF-IDF analytics', 'Explore the numbers that make retrieval meaningful.'),
    'search': ('Search engine', 'Find exact phrases. Explore the relevance behind every result.'),
    'mathematics': ('Query mathematics', 'Follow a query from its first token to its final score.'),
    'reports': ('Export & report', 'Real calculations, ready for your next discussion.'),
}


def create_app(root=ROOT):
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
        return jsonify(error='Choose a smaller batch (under 2 MB per import).'), 413

    @app.after_request
    def response_headers(response):
        if request.endpoint != 'static':
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
        return render_template((page if g.collection else 'empty') + '.html', page=page, pages=PAGES,
                               title=PAGES[page][0], description=PAGES[page][1],
                               loaded=bool(g.collection), prefix=f'/c/{g.key}/' if g.collection else '/')

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
            buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name='ir-results.zip')
        if name not in exports:
            abort(404)
        return send_file(io.BytesIO(exports[name]), as_attachment=True, download_name=name)

    app.register_blueprint(views)
    app.register_blueprint(views, url_prefix='/c/<key>', name='active')
    return app


if __name__ == '__main__':
    from waitress import serve
    print('Technology IR is available at http://127.0.0.1:5000 — Ctrl+C to close.')
    serve(create_app(), host='127.0.0.1', port=5000)
