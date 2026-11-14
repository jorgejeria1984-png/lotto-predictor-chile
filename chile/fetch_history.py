"""Download candidate rows from a known public historical table; never silently approve them."""
import argparse
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from engine import Draw, PROFILES
from history import save_atomic

SOURCE='https://indicadoresydatos.cl/azar/estadisticas-loto-kino'
HEADERS={'loto':'matriz numérica (41 n)','kino':'14 números extraídos'}

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables=[]; self.table=None; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='table':
            self.table=[]
        elif tag=='tr' and self.table is not None:
            self.row=[]
        elif tag in ('td','th') and self.row is not None:
            self.cell=[]
        elif tag=='br' and self.cell is not None:
            self.cell.append(' ')
    def handle_data(self,data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        elif tag=='tr' and self.row is not None:
            self.table.append(self.row); self.row=None
        elif tag=='table' and self.table is not None:
            self.tables.append(self.table); self.table=None

def parse(html,game):
    parser=Tables(); parser.feed(html)
    matching=[table for table in parser.tables if any(any(HEADERS[game] in cell.casefold() for cell in row) for row in table)]
    if len(matching)!=1:
        raise ValueError('Expected exactly one identified game table; source structure changed')
    p=PROFILES[game]; result={}
    for row in matching[0]:
        if not row or not re.fullmatch(r'#?\s*\d+',row[0]):
            continue
        if len(row)!=3:
            raise ValueError('Unexpected column count in game table')
        number=int(row[0].lstrip('#').strip())
        if game=='loto' and number<2935 or game=='kino' and number<799:
            raise ValueError('Unexpected historical era')
        day=date.fromisoformat(row[1])
        if day>date.today():
            raise ValueError('Future date in source')
        tokens=row[2].split()
        expected=p.pick+(game=='loto')
        if len(tokens)!=expected or not all(t.isdecimal() for t in tokens):
            raise ValueError('Unexpected number cells; parser refuses to infer')
        nums=list(map(int,tokens))
        if len(set(nums))!=expected or any(not 1<=x<=p.pool for x in nums) or number in result:
            raise ValueError('Invalid or repeated balls/draw')
        result[number]=(Draw(number,day,frozenset(nums[:p.pick])),SOURCE)
    if not result:
        raise ValueError('No valid rows; no file written')
    return result

def download():
    req=Request(SOURCE,headers={'User-Agent':'LottoPredictorChile/1.0 research; manual review required'})
    with urlopen(req,timeout=20) as response:
        # Refuse off-site redirect and excessively large responses.
        if urlsplit(response.geturl()).hostname!=urlsplit(SOURCE).hostname:
            raise ValueError('Unexpected redirect')
        raw=response.read(4_000_001)
        if len(raw)>4_000_000:
            raise ValueError('Page too large')
        return raw.decode(response.headers.get_content_charset() or 'utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',required=True,choices=PROFILES)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    records=parse(download(),args.game)
    # Do not overwrite canonical datasets or an existing staging file.
    if args.output.exists() or args.output.resolve().parent.name=='data':
        parser.error('Choose a fresh staging file outside canonical data folder')
    save_atomic(args.output,records,args.game)
    print(f'{len(records)} candidate records downloaded. Verify against official operator before merging.')

if __name__=='__main__':
    main()
