"""Preenche lacunas do catalogo com Argos Translate local (EN -> PT)."""
import csv, sys
from pathlib import Path
import argostranslate.translate as translate

p=Path(sys.argv[1]); rows=list(csv.DictReader(p.open(encoding='utf-8',newline='')))
cache={}
for r in rows:
    if r['pt_br']: cache[r['en']]=r['pt_br']
missing=[]
for r in rows:
    if not r['pt_br'] and r['en'] not in missing: missing.append(r['en'])
for i, source in enumerate(missing,1):
    try: cache[source]=translate.translate(source,'en','pt')
    except Exception as e: cache[source]=source
    if i%100==0: print(f'{i}/{len(missing)}',flush=True)
for r in rows:
    if not r['pt_br']:
        r['pt_br']=cache[r['en']]
        r['status']='machine-draft'
with p.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print('concluido',len(missing))
