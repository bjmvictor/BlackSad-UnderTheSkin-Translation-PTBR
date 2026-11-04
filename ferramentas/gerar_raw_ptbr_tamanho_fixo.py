"""Cria TextAsset PT-BR mantendo cada campo no tamanho do Script arabe funcional."""
from __future__ import annotations
import csv, struct, sys
from pathlib import Path
import importlib.util

spec=importlib.util.spec_from_file_location('format',Path(__file__).with_name('gerar_raw_uabea_ptbr.py'))
fmt=importlib.util.module_from_spec(spec); spec.loader.exec_module(fmt)

def fit(text: str, size: int) -> tuple[bytes,bool]:
    raw=text.encode('utf-8')
    if len(raw)<=size: return raw+b' '*(size-len(raw)), True
    # Do not emit invalid UTF-8; use the longest complete prefix that fits.
    clipped=raw[:size]
    while clipped:
        try: clipped.decode('utf-8'); break
        except UnicodeDecodeError: clipped=clipped[:-1]
    return clipped+b' '*(size-len(clipped)), False

def main(raw_path,catalog,arab_bundle,target):
    blob=raw_path.read_bytes(); name_len=struct.unpack_from('<I',blob,0)[0]; start=4+name_len; start+=(4-start%4)%4
    old_len=struct.unpack_from('<I',blob,start)[0]; original=blob[start+4:start+4+old_len]
    arab=bytearray(fmt.get_script(arab_bundle))
    original_records=list(fmt.records(original,False)); arab_records=list(fmt.records(arab,False))
    if len(original_records)!=len(arab_records): raise SystemExit('Estruturas originais e arabe incompativeis')
    mapping={r['en']:r['pt_br'] for r in csv.DictReader(catalog.open(encoding='utf-8',newline='')) if r['pt_br']}
    full=truncated=fallback=0
    for original_record, arab_record in zip(original_records,arab_records):
        source=original_record[0]; text=mapping.get(source,source)
        begin=arab_record[1]+4; end=arab_record[2]; capacity=end-begin
        written,ok=fit(text,capacity)
        if not ok:
            written,english_ok=fit(source,capacity); fallback+=1
        else: full+=1
        arab[begin:end]=written
    padding=b'\0'*((4-len(arab)%4)%4)
    target.write_bytes(blob[:start]+struct.pack('<I',len(arab))+arab+padding+blob[start+4+old_len:])
    print(f'Gerado: {target}; PT-BR integral em {full}; ingles preservado por limite em {fallback}; bytes {target.stat().st_size}')

if __name__=='__main__': main(*(Path(x) for x in sys.argv[1:]))
