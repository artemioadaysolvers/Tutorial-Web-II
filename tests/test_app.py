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
    def start_flow(self):
        self.app.config.update(GITHUB_CLIENT_ID='client', GITHUB_CLIENT_SECRET='secret', APP_URL='https://example.test')
        response = self.client.get('/auth/login')
        from urllib.parse import urlparse, parse_qs
        query = parse_qs(urlparse(response.location).query)
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertNotIn('secret', response.location)
        return query['state'][0]

    @patch('server.urlopen')
    def test_github_callback(self, remote):
        import io, json, hashlib
        state = self.start_flow()
        remote.side_effect = [io.BytesIO(json.dumps({'access_token':'TOKEN'}).encode()),
            io.BytesIO(json.dumps({'id':123, 'login':'ana', 'name':'Ana'}).encode())]
        self.assertEqual(self.client.get('/auth/callback', query_string={'state':state,'code':'CODE'}).status_code,302)
        with self.client.session_transaction() as session:
            self.assertEqual(session['user']['name'],'Ana')
            self.assertEqual(session['user']['id'],hashlib.sha256(b'github|123').hexdigest())
            self.assertNotIn('TOKEN',str(dict(session)))
            self.assertNotIn('flow',session)
        self.assertEqual(self.client.get('/auth/callback',query_string={'state':state,'code':'CODE'}).status_code,400)
        self.assertEqual(remote.call_count,2)
        token_request = remote.call_args_list[0].args[0]
        self.assertIn(b'code_verifier=', token_request.data)
        self.assertEqual(remote.call_args_list[1].args[0].get_header('Authorization'),'Bearer TOKEN')

    @patch('server.urlopen')
    def test_invalid_state(self, remote):
        self.start_flow()
        self.assertEqual(self.client.get('/auth/callback?state=wrong&code=x').status_code,400)
        remote.assert_not_called()

    @patch('server.urlopen')
    def test_expired_flow(self, remote):
        state=self.start_flow()
        with self.client.session_transaction() as session: session['flow_started']=1
        self.assertEqual(self.client.get('/auth/callback',query_string={'state':state,'code':'x'}).status_code,400)
        remote.assert_not_called()

    @patch('server.urlopen')
    def test_denied_login(self, remote):
        state=self.start_flow()
        self.assertEqual(self.client.get('/auth/callback',query_string={'state':state,'error':'access_denied'}).status_code,400)
        remote.assert_not_called()

    @patch('server.urlopen')
    def test_token_error(self, remote):
        import io
        state=self.start_flow()
        remote.return_value=io.BytesIO(b'{"error":"bad_verification_code"}')
        self.assertEqual(self.client.get('/auth/callback',query_string={'state':state,'code':'bad'}).status_code,400)
        with self.client.session_transaction() as session: self.assertNotIn('user',session)

    @patch('server.urlopen')
    def test_invalid_profile(self, remote):
        import io
        state=self.start_flow()
        remote.side_effect=[io.BytesIO(b'{"access_token":"token"}'),io.BytesIO(b'{"login":"ana"}')]
        self.assertEqual(self.client.get('/auth/callback',query_string={'state':state,'code':'x'}).status_code,400)

    @patch('server.urlopen')
    def test_network_error(self, remote):
        from urllib.error import URLError
        state=self.start_flow()
        remote.side_effect=URLError('unavailable')
        self.assertEqual(self.client.get('/auth/callback',query_string={'state':state,'code':'x'}).status_code,400)

    def test_logout(self):
        self.login()
        self.assertEqual(self.client.post('/auth/logout',data={'csrf':'test-csrf'}).status_code,302)
        self.assertEqual(self.client.get('/api/recados').status_code,401)
    def test_health(self):
        self.assertEqual(self.client.get('/health').json,{'status':'ok'})

if __name__=='__main__': unittest.main()
