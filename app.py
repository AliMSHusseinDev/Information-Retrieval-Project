"""Thin Flask routes. All retrieval mathematics lives in src/, independently of HTTP."""

import io
import sys
import zipfile
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file, abort
from src.exports import EXPORT_FILES
from src.queries import PRESETS, search
from src.storage import load_model

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
    """Create a local application; fail clearly if Spark preprocessing needs rebuilding."""
    model = load_model(root)
    app = Flask(__name__, template_folder=str(root / 'templates'), static_folder=str(root / 'static'))
    app.json.sort_keys = False  # Keep d1, d2, ..., d10 in natural order in the browser.
    app.config['MAX_CONTENT_LENGTH'] = 4096

    def check_current_model():
        """Reject stale disk data and a rebuilt cache until the app is restarted."""
        current = load_model(root)
        if current['metadata'] != model['metadata']:
            raise RuntimeError('Processing outputs were rebuilt. Restart the application to load them.')

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        return response

    @app.get('/')
    @app.get('/<page>')
    def page_view(page='dashboard'):
        if page not in PAGES:
            abort(404)
        return render_template(page + '.html', page=page, pages=PAGES,
                               title=PAGES[page][0], description=PAGES[page][1],
                               document_count=len(model['documents']))

    @app.get('/api/model')
    def model_data():
        # Do not silently serve old statistics if documents change while Flask runs.
        check_current_model()
        return jsonify(model=model, presets=PRESETS)

    @app.get('/api/health')
    def health():
        check_current_model()
        return jsonify(application='lumen-ir', fingerprint=model['metadata']['fingerprint'])

    @app.get('/api/index')
    def index_data():
        check_current_model()
        term = request.args.get('term', '').lower().strip()
        return jsonify(model['index'].get(term, {}) if term else model['index'])

    @app.post('/api/search')
    def search_data():
        check_current_model()
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error='Send a JSON object containing a phrase and mode.'), 400
        try:
            return jsonify(search(model, body.get('phrase'), body.get('mode', 'phrase'), body.get('other', '')))
        except (ValueError, TypeError):
            # Validation errors are expected user input, not server tracebacks.
            return jsonify(error='Enter a phrase (up to 300 characters / 40 tokens) and a valid search mode. Boolean modes require two phrases.'), 400

    @app.get('/api/exports')
    def export_status():
        check_current_model()
        return jsonify([dict(name=name, ready=(root / 'outputs' / name).is_file(),
                             bytes=(root / 'outputs' / name).stat().st_size if (root / 'outputs' / name).is_file() else 0)
                        for name in EXPORT_FILES])

    @app.get('/download/<name>')
    def download(name):
        check_current_model()
        if name == 'all.zip':
            if any(not (root / 'outputs' / file).is_file() for file in EXPORT_FILES):
                return jsonify(error='Some outputs are missing. Run python run_spark.py.'), 409
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                for file in EXPORT_FILES:
                    archive.write(root / 'outputs' / file, file)
            buffer.seek(0)
            return send_file(buffer, mimetype='application/zip', as_attachment=True, download_name='technology-ir-results.zip')
        if name not in EXPORT_FILES or not (root / 'outputs' / name).is_file():
            abort(404)
        return send_file(root / 'outputs' / name, as_attachment=True)

    @app.errorhandler(RuntimeError)
    def stale_outputs(error):
        return jsonify(error=str(error)), 409

    return app


if __name__ == '__main__':
    from waitress import serve
    print('Technology IR is available at http://127.0.0.1:5000 — Ctrl+C to close.')
    serve(create_app(), host='127.0.0.1', port=5000)
