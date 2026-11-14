"""Local-only browser interface and CLI; Python standard library."""
import argparse, io, json, html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
from engine import PROFILES, load_csv, analyze
from advanced import load_history, replay, bias_report

PAGE='''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Lotto Predictor Chile</title><style>body{font:16px system-ui;max-width:960px;margin:40px auto;padding:0 20px;color:#223344}label{display:block;margin:14px 0}textarea{width:100%;height:220px}button{background:#164b78;color:white;padding:10px 18px;border:0;border-radius:6px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}.balls{font-size:1.35rem;font-weight:bold;word-spacing:6px;color:#164b78}small{color:#52626e}</style><h1>Lotto Predictor Chile</h1><p>Exploración estadística de sorteos principales. No garantiza premios.</p><form method="post"><label>Juego <select name="game"><option value="loto">Loto 6/41</option><option value="kino">Kino 14/25</option></select></label><label>Historial CSV (draw,date,n1,...,n6 o n14)<textarea name="csv" required placeholder="Pegue el historial de resultados verificados; mínimo 80 sorteos."></textarea></label><button>Analizar historial</button></form>'''

def render(result):
    text=html.escape
    rows=''.join('<tr><td>'+text(s)+'</td><td>'+f"{result['entrenamiento'][s]['media']:.3f}</td><td>{v['media']:.3f}</td><td>{v['objetivo_aciertos']}/{v['sorteos']}</td></tr>" for s,v in result['validacion'].items())
    balls=' · '.join(f'{n:02d}' for n in result['combinacion'])
    return (f"<h2>Resultado experimental</h2><p>Último sorteo: {result['ultimo_sorteo']} · {result['ultima_fecha']}</p><p>Modelo seleccionado: {text(result['estrategia'])}</p><p class='balls'>{balls}</p>"
            f"<p>Media aleatoria teórica: {result['azar_media_teorica']:.3f}; objetivo: ≥{result['objetivo']} aciertos; p-valor unilateral en validación: {result['p_valor_unilateral_objetivo']:.4f}.</p>"
            '<table><thead><tr><th>Estrategia</th><th>Media selección</th><th>Media prueba</th><th>Objetivo en prueba</th></tr></thead><tbody>'+rows+'</tbody></table><p>'+text(result['advertencia'])+'</p>')

class Handler(BaseHTTPRequestHandler):
    def respond(self,body,status=200):
        data=(PAGE+body).encode(); self.send_response(status); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def respond_json(self, data, status=200):
        payload=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(payload)
    def do_GET(self):
        url=urlsplit(self.path)
        if url.path!='/chile-api/analysis':
            self.respond('')
            return
        try:
            game=parse_qs(url.query,max_num_fields=2).get('game',['loto'])[0]
            p=PROFILES[game]
            h=load_history(game)
            result=replay(h,p,simulations=10000)
            result['diagnostico_sesgo']=bias_report(h,p)
            result['registros']=len(h)
            result['fecha_ultimo']=str(h[-1].date)
            self.respond_json(result)
        except (ValueError,KeyError,OSError) as exc:
            self.respond_json({'error':str(exc)},400)

    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>5_000_000: raise ValueError('Tamaño de entrada inválido')
            form=parse_qs(self.rfile.read(length).decode(),max_num_fields=4)
            p=PROFILES[form['game'][0]]; draws=load_csv(io.StringIO(form['csv'][0]),p)
            self.respond(render(analyze(draws,p)))
        except (ValueError,KeyError,TypeError) as exc:
            self.respond('<p>Error: '+html.escape(str(exc))+'</p>',400)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--game',choices=PROFILES); parser.add_argument('--csv'); parser.add_argument('--port',type=int,default=8765); args=parser.parse_args()
    if args.csv:
        if not args.game: parser.error('--csv requiere --game')
        with open(args.csv,encoding='utf-8-sig',newline='') as f: result=analyze(load_csv(f,PROFILES[args.game]),PROFILES[args.game])
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(f'http://127.0.0.1:{args.port}',flush=True); HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
if __name__=='__main__': main()
