"""Gera uma planilha sem duplicatas para revisao humana do PT-BR."""
from __future__ import annotations
import csv, sys
from collections import Counter
from pathlib import Path

def main(source: Path, target: Path) -> None:
    with source.open(encoding='utf-8', newline='') as file:
        rows=list(csv.DictReader(file))
    counts=Counter(row['en'] for row in rows)
    unique={}
    for row in rows:
        unique.setdefault(row['en'], row)
    fields=('id','en','pt_br','es','fr','de','it','nl','ru','occurrences','status','notes')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields)
        writer.writeheader()
        for row in unique.values():
            writer.writerow({field: counts[row['en']] if field=='occurrences' else row.get(field,'') for field in fields})
    print(f'{len(unique)} textos distintos em {target}')

if __name__=='__main__': main(Path(sys.argv[1]),Path(sys.argv[2]))
