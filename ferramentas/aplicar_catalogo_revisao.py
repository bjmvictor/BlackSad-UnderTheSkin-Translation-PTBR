"""Propaga as correcoes da planilha unica para todas as ocorrencias do catalogo."""
from __future__ import annotations
import csv, sys
from pathlib import Path

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as file: return list(csv.DictReader(file))
def main(catalog: Path, review: Path):
    rows=read(catalog); review_rows=read(review)
    changes={r['en']:r for r in review_rows if r.get('pt_br')}
    changed=0
    for row in rows:
        if row['en'] in changes:
            source=changes[row['en']]
            if row['pt_br']!=source['pt_br'] or row['status']!=source['status'] or row['notes']!=source['notes']:
                row['pt_br']=source['pt_br']; row['status']=source['status']; row['notes']=source['notes']; changed+=1
    with catalog.open('w',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    print(f'{changed} ocorrencias atualizadas')
if __name__=='__main__': main(Path(sys.argv[1]),Path(sys.argv[2]))
