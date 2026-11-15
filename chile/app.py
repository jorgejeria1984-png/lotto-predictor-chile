"""Local dashboard and backward-compatible analysis API/CLI."""
import argparse
import sys
from functools import lru_cache
import json
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from engine import PROFILES, load_csv, analyze
from dashboard import Dashboard

ROOT=Path(__file__).resolve().parent
TOKEN=secrets.token_urlsafe(32)

@lru_cache(maxsize=1)
def neural_status():
    if getattr(sys,'frozen',False):
        return {'available':False,'version':None,'message':'El EXE portátil no incluye PyTorch. Use ABRIR_LOTTO.cmd para activar LSTM.'}
    try:
        import torch
        # Verify actual CPU operation, not only the presence of a package.
        torch.zeros(1,device='cpu').add_(1)
        return {'available':True,'version':str(torch.__version__),'message':'PyTorch CPU disponible'}
    except (ImportError,OSError,RuntimeError) as exc:
        return {'available':False,'version':None,'message':'PyTorch no disponible en este Python: '+str(exc)}

class Handler(BaseHTTPRequestHandler):
    dashboard=Dashboard()

    def allowed_host(self):
        return self.headers.get('Host','') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

    def respond(self,data,kind,status=200):
        payload=data.encode('utf-8') if isinstance(data,str) else data
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def json(self,data,status=200):
        self.respond(json.dumps(data,ensure_ascii=False),'application/json; charset=utf-8',status)

    def do_GET(self):
        if not self.allowed_host():
            self.json({'error':'Host no permitido'},403);return
        url=urlsplit(self.path)
        try:
            if url.path=='/':
                self.respond((ROOT/'web'/'index.html').read_text(encoding='utf-8').replace('__LOCAL_TOKEN__',TOKEN),'text/html; charset=utf-8')
                return
            assets={'/dashboard.js':('dashboard.js','text/javascript; charset=utf-8'),'/dashboard.css':('dashboard.css','text/css; charset=utf-8'),'/lab.js':('lab.js','text/javascript; charset=utf-8')}
            if url.path in assets:
                name,kind=assets[url.path];self.respond((ROOT/'web'/name).read_bytes(),kind);return
            q=parse_qs(url.query,max_num_fields=8)
            game=q.get('game',['loto'])[0]
            if url.path=='/chile-api/capabilities':
                self.json(neural_status())
            elif url.path=='/chile-api/analysis':
                self.json(self.dashboard.analysis(game,lstm=q.get('lstm',['0'])[0]=='1',refresh=q.get('refresh',['0'])[0]=='1'))
            elif url.path=='/chile-api/history':
                self.json(self.dashboard.history(game,int(q.get('offset',['0'])[0]),int(q.get('limit',['25'])[0])))
            elif url.path=='/chile-api/ledger':
                self.json(self.dashboard.ledger(game))
            else:
                self.json({'error':'Ruta inexistente'},404)
        except (ValueError,KeyError,OSError,RuntimeError,sqlite3.Error) as exc:
            self.json({'error':str(exc)},400)

    def do_POST(self):
        origin=self.headers.get('Origin','')
        expected='http://'+self.headers.get('Host','')
        if not self.allowed_host() or origin!=expected or not secrets.compare_digest(self.headers.get('X-Chile-Token',''),TOKEN):
            self.json({'error':'Solicitud local no autorizada'},403);return
        try:
            if self.headers.get_content_type()!='application/json':
                raise ValueError('Se requiere JSON')
            length=int(self.headers.get('Content-Length','0'))
            if not 1<=length<=16000:
                raise ValueError('Tamaño inválido')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):
                raise ValueError('Formato inválido')
            game=data['game']
            if not isinstance(game,str) or game not in PROFILES:
                raise ValueError('Juego inválido')
            route=urlsplit(self.path).path
            if route=='/chile-api/stage':
                result=self.dashboard.stage(game)
            elif route=='/chile-api/approve':
                result=self.dashboard.approve(game,data['stage_hash'],data.get('reviewed'))
            elif route=='/chile-api/freeze':
                result=self.dashboard.freeze(game,data['deadline'],data.get('reviewed'),data.get('lstm') is True)
            elif route=='/chile-api/simulate':
                result=self.dashboard.simulate(game,data['weights'])
            elif route=='/chile-api/settle':
                result=self.dashboard.settle(game,data.get('reviewed'))
            else:
                self.json({'error':'Ruta inexistente'},404);return
            self.json(result)
        except (ValueError,KeyError,TypeError,OSError,RuntimeError,sqlite3.Error) as exc:
            self.json({'error':str(exc)},400)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--game',choices=PROFILES);parser.add_argument('--csv');parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if args.csv:
        if not args.game:parser.error('--csv requiere --game')
        with open(args.csv,encoding='utf-8-sig',newline='') as file:
            result=analyze(load_csv(file,PROFILES[args.game]),PROFILES[args.game])
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(f'http://127.0.0.1:{args.port}',flush=True)
        HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

if __name__=='__main__':main()
