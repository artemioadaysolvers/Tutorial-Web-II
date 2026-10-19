import base64
import hashlib
import unittest
from html.parser import HTMLParser
from pathlib import Path
from server import create_app
from test_app import MemoryStore

OUT=Path(__file__).resolve().parents[1]/'frontend'/'out'

class Assets(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.assets=[]; self.inline=False; self.parts=[]; self.scripts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script':
            if a.get('src'): self.assets.append(a['src'])
            self.inline=not a.get('src'); self.parts=[]
        if tag=='link' and a.get('rel')=='stylesheet': self.assets.append(a['href'])
    def handle_data(self,data):
        if self.inline: self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.inline:
            self.scripts.append(''.join(self.parts)); self.inline=False

@unittest.skipUnless((OUT/'index.html').is_file(),'Primero construir el frontend con npm run build')
class ExportTests(unittest.TestCase):
    def test_python_serves_next_export_with_valid_csp(self):
        app=create_app({'TESTING':True,'SECRET_KEY':'x'*64},MemoryStore())
        client=app.test_client()
        with client.get('/') as response:
            self.assertEqual(response.status_code,200)
            parser=Assets(); parser.feed(response.get_data(as_text=True))
            csp=response.headers['Content-Security-Policy']
        self.assertTrue(parser.assets)
        self.assertTrue(parser.scripts)
        for script in parser.scripts:
            digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
            self.assertIn("'sha256-"+digest+"'",csp)
        for asset in parser.assets:
            with self.subTest(asset=asset), client.get(asset) as response:
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.get_data())
        with client.get('/_next/../../server.py') as response:
            self.assertEqual(response.status_code,404)
        self.assertEqual(client.get('/api/recados').status_code,401)
