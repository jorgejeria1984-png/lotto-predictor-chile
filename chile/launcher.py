"""Windows and source launcher; keep mutable records beside the executable."""
from pathlib import Path
import shutil
import sys
import threading
import webbrowser
from http.server import HTTPServer
from app import Handler,ROOT,neural_status
from dashboard import Dashboard

def main():
    if getattr(sys,'frozen',False):
        home=Path(sys.executable).resolve().parent
        data=home/'data'
        data.mkdir(exist_ok=True)
        for game in ('loto','kino'):
            dest=data/f'{game}.csv'
            if not dest.exists():
                shutil.copy2(ROOT/'data'/dest.name,dest)
        Handler.dashboard=Dashboard(data,home/'staging',home/'prospective.sqlite')
    capability=neural_status()
    print(capability['message']+((' '+capability['version']) if capability['available'] else ''),flush=True)
    # Bind before opening the browser, avoiding another app on an occupied port.
    try:
        server=HTTPServer(('127.0.0.1',8765),Handler)
    except OSError:
        server=HTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}/'
    print('Lotto Predictor Chile 3.1\n'+url+'\nMantenga esta ventana abierta. Ctrl+C para cerrar.',flush=True)
    threading.Timer(.4,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
