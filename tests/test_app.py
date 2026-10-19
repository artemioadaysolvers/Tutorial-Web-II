import tempfile
import unittest
from unittest.mock import patch, Mock
from pathlib import Path
from server import create_app
class MemoryStore:
    """Doble de pruebas; la aplicación usa Cosmos DB exclusivamente."""
    def __init__(self): self.rows={}
    def list(self, owner): return [{k:v for k,v in r.items() if k!='owner'} for r in self.rows.values() if r['owner']==owner]
    def save(self, note): self.rows[note['id']]=note.copy()
    def delete(self, owner, id):
        if id not in self.rows or self.rows[id]['owner']!=owner: return False
        del self.rows[id]
        return True
    def health(self): pass


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.frontend=Path(self.temp.name)
        (self.frontend/'index.html').write_text('<!doctype html><html><script>self.ready=true</script></html>',encoding='utf-8')
        self.store=MemoryStore()
        self.app=create_app({'TESTING':True,'SECRET_KEY':'x'*64,'FRONTEND_DIR':str(self.frontend)},self.store)
        self.client=self.app.test_client()
    def tearDown(self):
        self.temp.cleanup()
    def login(self,owner='alice'):
        with self.client.session_transaction() as s:
            s['user']={'id':owner,'name':'Persona'}
            s['csrf']='test-csrf'
    def add(self,body='Mi recado'):
        return self.client.post('/api/recados',json={'body':body},headers={'X-CSRF-Token':'test-csrf'})
    def test_anonymous_denied(self):
        self.assertEqual(self.client.get('/api/recados').status_code,401)
        self.assertEqual(self.add().status_code,401)
    def test_public_session(self):
        response=self.client.get('/api/session')
        self.assertIsNone(response.json['user'])
        self.assertTrue(response.json['csrf'])
        self.login()
        self.assertEqual(self.client.get('/api/session').json['user'],{'name':'Persona'})

    def test_csrf(self):
        self.login()
        self.assertEqual(self.client.post('/api/recados',json={'body':'x'}).status_code,403)
    def test_owner_isolation(self):
        self.login()
        res=self.add(); self.assertEqual(res.status_code,201)
        id=res.json['recado']['id']
        self.assertEqual(len(self.store.list('alice')),1)
        self.login('bob')
        self.assertEqual(self.client.get('/api/recados').json['recados'],[])
        self.assertEqual(self.client.delete('/api/recados/'+id,headers={'X-CSRF-Token':'test-csrf'}).status_code,404)
        self.login()
        self.assertEqual(self.client.delete('/api/recados/'+id,headers={'X-CSRF-Token':'test-csrf'}).status_code,204)
        self.assertEqual(self.client.get('/api/recados').json['recados'],[])
    def test_validation(self):
        self.login()
        for body in (' ','x'*2001,34,None):
            self.assertEqual(self.add(body).status_code,400)
    def test_content_and_headers(self):
        self.login()
        self.assertEqual(self.add('<script>alert(1)</script>').json['recado']['body'],'<script>alert(1)</script>')
        response=self.client.get('/')
        self.assertIn('script-src',response.headers['Content-Security-Policy'])
        self.assertEqual(response.status_code,200)
        self.assertIn('sha256-',response.headers['Content-Security-Policy'])
        self.assertNotIn("'unsafe-inline'",response.headers['Content-Security-Policy'])
        response.close()
    def test_auth_requires_real_flow(self):
        self.assertEqual(self.client.get('/auth/callback?code=forged').status_code,400)
    @patch('server.msal.ConfidentialClientApplication')
    def test_microsoft_callback(self,klass):
        from datetime import datetime,timezone
        with self.client.session_transaction() as s:
            s['flow']={'state':'value'}
            s['flow_started']=datetime.now(timezone.utc).timestamp()
        klass.return_value.acquire_token_by_auth_code_flow.return_value={'id_token_claims':{'iss':'https://issuer/','sub':'subject','name':'Ana'}}
        self.assertEqual(self.client.get('/auth/callback?state=value&code=test').status_code,302)
        with self.client.session_transaction() as s:
            self.assertEqual(s['user']['name'],'Ana')
            self.assertNotIn('flow',s)
    @patch('server.msal.ConfidentialClientApplication')
    def test_invalid_state(self,klass):
        from datetime import datetime,timezone
        with self.client.session_transaction() as s:
            s['flow']={'state':'expected'}; s['flow_started']=datetime.now(timezone.utc).timestamp()
        klass.return_value.acquire_token_by_auth_code_flow.side_effect=ValueError('state mismatch')
        self.assertEqual(self.client.get('/auth/callback?state=wrong').status_code,400)
    def test_logout(self):
        self.login()
        self.assertEqual(self.client.post('/auth/logout',data={'csrf':'test-csrf'}).status_code,302)
        self.assertEqual(self.client.get('/api/recados').status_code,401)
    def test_health(self):
        self.assertEqual(self.client.get('/health').json,{'status':'ok'})

if __name__=='__main__': unittest.main()
