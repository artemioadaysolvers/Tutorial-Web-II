import base64
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from urllib.parse import urlencode
import json
from urllib.request import Request, urlopen
from urllib.error import URLError
from flask import Flask, jsonify, redirect, render_template, request, session, send_from_directory
from werkzeug.exceptions import HTTPException
from store import CosmosStore


def create_app(config=None, store=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY'),
        GITHUB_CLIENT_ID=os.getenv('GITHUB_CLIENT_ID',''),
        GITHUB_CLIENT_SECRET=os.getenv('GITHUB_CLIENT_SECRET',''),
        APP_URL=os.getenv('APP_URL','').rstrip('/'),
        FRONTEND_DIR=str(Path(__file__).parent/'frontend'/'out'),
        MAX_CONTENT_LENGTH=16384, SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if config:
        app.config.update(config)
    if not app.secret_key or len(app.secret_key) < 32 or app.secret_key.startswith('REEMPLAZAR'):
        raise ValueError('Configura SECRET_KEY con al menos 32 caracteres aleatorios')
    app.config['SESSION_COOKIE_SECURE'] = app.config['APP_URL'].startswith('https://')
    if os.getenv('WEBSITE_SITE_NAME') and not app.config['SESSION_COOKIE_SECURE']:
        raise ValueError('Azure requiere APP_URL con HTTPS')
    if not app.testing and not app.config['SESSION_COOKIE_SECURE']:
        raise ValueError('Configura APP_URL con la dirección HTTPS pública de Azure')
    if not store:
        store = CosmosStore(os.environ['COSMOS_ENDPOINT'],os.environ['COSMOS_KEY'],os.getenv('COSMOS_DATABASE','RecadosDB'),os.getenv('COSMOS_CONTAINER','recados'))
    app.extensions['store'] = store

    def github_json(url, data=None, token=None):
        headers = {'Accept': 'application/json', 'User-Agent': 'Recados-Web'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        payload = None
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            payload = urlencode(data).encode('utf-8')
        req = Request(url, data=payload, headers=headers)
        with urlopen(req, timeout=15) as response:
            return json.load(response)

    @app.before_request
    def protect():
        if request.path.startswith('/api/') and request.path != '/api/session':
            if not session.get('user'):
                return jsonify(error='Inicia sesión para continuar.'),401
        if request.method in ('POST','DELETE','PUT','PATCH'):
            expected = session.get('csrf','')
            supplied = request.headers.get('X-CSRF-Token','') or request.form.get('csrf','')
            if not expected or not hmac.compare_digest(expected,supplied):
                return jsonify(error='La sesión cambió. Recarga la página.'),403

    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self' "+script_hashes+"; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    class InlineScripts(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.inline=False
            self.parts=[]
            self.hashes=[]
        def handle_starttag(self,tag,attrs):
            if tag == 'script':
                self.inline='src' not in dict(attrs)
                self.parts=[]
        def handle_data(self,data):
            if self.inline:
                self.parts.append(data)
        def handle_endtag(self,tag):
            if tag=='script' and self.inline:
                digest=base64.b64encode(hashlib.sha256(''.join(self.parts).encode()).digest()).decode()
                self.hashes.append("'sha256-"+digest+"'")
                self.inline=False
    frontend=Path(app.config['FRONTEND_DIR'])
    parser=InlineScripts()
    if (frontend/'index.html').is_file():
        parser.feed((frontend/'index.html').read_text(encoding='utf-8'))
    elif not app.testing:
        raise ValueError('Falta construir el frontend Next.js: usa el Dockerfile incluido')
    script_hashes=' '.join(parser.hashes)

    @app.get('/')
    def home():
        return send_from_directory(frontend,'index.html')

    @app.get('/_next/<path:filename>')
    def next_assets(filename):
        return send_from_directory(frontend/'_next',filename)

    @app.get('/api/session')
    def current_session():
        session.setdefault('csrf',secrets.token_urlsafe(32))
        user=session.get('user')
        return jsonify(user={'name':user['name']} if user else None,csrf=session['csrf'])

    @app.get('/auth/login')
    def login():
        if not app.config['GITHUB_CLIENT_ID'] or not app.config['GITHUB_CLIENT_SECRET']:
            return render_template('error.html', message='Falta configurar el acceso de GitHub.'), 503
        session.clear()
        session.permanent = True
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        session['flow'] = {'state': state, 'verifier': verifier}
        session['flow_started'] = datetime.now(timezone.utc).timestamp()
        query = urlencode({'client_id': app.config['GITHUB_CLIENT_ID'],
            'redirect_uri': app.config['APP_URL'] + '/auth/callback',
            'state': state, 'scope': '', 'prompt': 'select_account', 'code_challenge': challenge,
            'code_challenge_method': 'S256'})
        return redirect('https://github.com/login/oauth/authorize?' + query)

    @app.get('/auth/callback')
    def callback():
        flow = session.pop('flow', None)
        started = session.pop('flow_started', 0)
        state = request.args.get('state', '')
        code = request.args.get('code', '')
        if (not flow or datetime.now(timezone.utc).timestamp() - started > 600
                or not state or not hmac.compare_digest(flow.get('state', ''), state)):
            return render_template('error.html', message='El acceso venció o no es válido. Vuelve a iniciar sesión.'), 400
        if request.args.get('error') or not code:
            return render_template('error.html', message='No se completó la autorización de GitHub.'), 400
        try:
            result = github_json('https://github.com/login/oauth/access_token', data={
                'client_id': app.config['GITHUB_CLIENT_ID'],
                'client_secret': app.config['GITHUB_CLIENT_SECRET'], 'code': code,
                'redirect_uri': app.config['APP_URL'] + '/auth/callback',
                'code_verifier': flow['verifier']})
            token = result.get('access_token')
            if result.get('error') or not isinstance(token, str) or not token:
                raise ValueError('No access token')
            profile = github_json('https://api.github.com/user', token=token)
            uid = profile.get('id')
            if type(uid) is not int or uid <= 0 or not isinstance(profile.get('login'), str) or not profile['login']:
                raise ValueError('Invalid GitHub identity')
        except (URLError, OSError, ValueError, TypeError, KeyError, AttributeError):
            return render_template('error.html', message='No se pudo completar el acceso con GitHub. Intenta nuevamente.'), 400
        owner = hashlib.sha256(('github|' + str(uid)).encode()).hexdigest()
        session.clear()
        session.permanent = True
        session['user'] = {'id': owner, 'name': profile.get('name') or profile['login']}
        session['csrf'] = secrets.token_urlsafe(32)
        return redirect('/')

    @app.post('/auth/logout')
    def logout():
        session.clear()
        return redirect('/')

    @app.get('/api/recados')
    def list_notes():
        return jsonify(recados=store.list(session['user']['id']))

    @app.post('/api/recados')
    def add_note():
        data=request.get_json(silent=True)
        body=data.get('body') if isinstance(data,dict) else None
        if not isinstance(body,str) or not body.strip() or not 1<=len(body)<=2000:
            return jsonify(error='Escribe un texto de 1 a 2000 caracteres.'),400
        note={'id':str(uuid4()),'owner':session['user']['id'],'body':body,'created':datetime.now(timezone.utc).isoformat()}
        store.save(note)
        return jsonify(recado={k:v for k,v in note.items() if k!='owner'}),201

    @app.delete('/api/recados/<uuid:id>')
    def delete_note(id):
        if not store.delete(session['user']['id'],str(id)):
            return jsonify(error='Texto no encontrado.'),404
        return '',204

    @app.get('/health')
    def health():
        store.health()
        return jsonify(status='ok')

    @app.errorhandler(Exception)
    def error(exc):
        if isinstance(exc,HTTPException):
            return jsonify(error='Solicitud no válida.'),exc.code
        app.logger.error('Falló una operación del servidor: %s',type(exc).__name__)
        if request.path.startswith('/api/') or request.path=='/health':
            return jsonify(error='Servicio no disponible. Intenta nuevamente.'),503
        return render_template('error.html',message='Servicio no disponible. Intenta nuevamente.'),503
    return app
