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
import msal
from flask import Flask, jsonify, redirect, render_template, request, session, send_from_directory
from werkzeug.exceptions import HTTPException
from store import CosmosStore


def create_app(config=None, store=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY'),
        MICROSOFT_CLIENT_ID=os.getenv('MICROSOFT_CLIENT_ID',''),
        MICROSOFT_CLIENT_SECRET=os.getenv('MICROSOFT_CLIENT_SECRET',''),
        MICROSOFT_TENANT=os.getenv('MICROSOFT_TENANT','common'),
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

    def identity():
        return msal.ConfidentialClientApplication(app.config['MICROSOFT_CLIENT_ID'], authority='https://login.microsoftonline.com/'+app.config['MICROSOFT_TENANT'], client_credential=app.config['MICROSOFT_CLIENT_SECRET'])

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
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self' "+script_hashes+"; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self' https://login.microsoftonline.com"})
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
        if not app.config['MICROSOFT_CLIENT_ID'] or not app.config['MICROSOFT_CLIENT_SECRET']:
            return render_template('error.html',message='Falta configurar el acceso de Microsoft. Consulta README.md.'),503
        session.clear()
        session.permanent=True
        session['flow']=identity().initiate_auth_code_flow(scopes=[],redirect_uri=app.config['APP_URL']+'/auth/callback')
        session['flow_started']=datetime.now(timezone.utc).timestamp()
        return redirect(session['flow']['auth_uri'])

    @app.get('/auth/callback')
    def callback():
        flow=session.pop('flow',None)
        started=session.pop('flow_started',0)
        if not flow or datetime.now(timezone.utc).timestamp()-started>600:
            return render_template('error.html',message='El acceso venció. Vuelve a iniciar sesión.'),400
        try:
            result=identity().acquire_token_by_auth_code_flow(flow,request.args.to_dict())
        except ValueError:
            result={}
        claims=result.get('id_token_claims',{})
        if not claims.get('sub') or not claims.get('iss'):
            return render_template('error.html',message='No se pudo completar el acceso con Microsoft.'),400
        owner=hashlib.sha256((claims['iss']+'|'+claims['sub']).encode()).hexdigest()
        session.clear()
        session.permanent=True
        session['user']={'id':owner,'name':claims.get('name','Usuario de Microsoft')}
        session['csrf']=secrets.token_urlsafe(32)
        return redirect('/')

    @app.post('/auth/logout')
    def logout():
        session.clear()
        query=urlencode({'post_logout_redirect_uri':app.config['APP_URL']+'/'})
        return redirect('https://login.microsoftonline.com/'+app.config['MICROSOFT_TENANT']+'/oauth2/v2.0/logout?'+query)

    @app.get('/api/recados')
    def list_notes():
        return jsonify(recados=store.list(session['user']['id']))

    @app.post('/api/recados')
    def add_note():
        data=request.get_json(silent=True)
        body=data.get('body') if isinstance(data,dict) else None
        if not isinstance(body,str) or not 1<=len(body.strip())<=2000:
            return jsonify(error='Escribe un recado de 1 a 2000 caracteres.'),400
        note={'id':str(uuid4()),'owner':session['user']['id'],'body':body.strip(),'created':datetime.now(timezone.utc).isoformat()}
        store.save(note)
        return jsonify(recado={k:v for k,v in note.items() if k!='owner'}),201

    @app.delete('/api/recados/<uuid:id>')
    def delete_note(id):
        if not store.delete(session['user']['id'],str(id)):
            return jsonify(error='Recado no encontrado.'),404
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
