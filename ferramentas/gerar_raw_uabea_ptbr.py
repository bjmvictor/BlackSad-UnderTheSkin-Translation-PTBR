"""Gera um TextAsset .dat para Import Raw no UABEA, sem reempacotar UnityFS."""
from __future__ import annotations
import bisect, csv, struct, sys
from collections import defaultdict
from pathlib import Path

IDS=(10,34,40,14,15,21,9,30)
HEAD=struct.pack('<II',8,10)

def entry(data,p):
    if p+8>len(data): return None
    lang,n=struct.unpack_from('<II',data,p); end=p+8+n
    if n>65536 or end>len(data): return None
    return lang,data[p+8:end],end

def records(data, require_ascii=True):
    at=0
    while True:
        h=data.find(HEAD,at)
        if h<0:return
        at=h+1;p=h+4;items=[]
        for _ in IDS:
            x=entry(data,p)
            if x is None: break
            items.append((p,*x));p=x[2]
        if len(items)!=8 or tuple(x[1] for x in items)!=IDS:continue
        try:s=items[0][2].decode('utf-8')
        except UnicodeDecodeError:continue
        if not s or (require_ascii and (not s.isascii() or any(ord(c)<32 or ord(c)>126 for c in s))):continue
        yield s,items[0][0]+4,items[0][3],p

def get_script(bundle):
    import UnityPy
    environment=UnityPy.load(str(bundle))
    for obj in environment.objects:
        if obj.type.name == 'TextAsset':
            return obj.read().m_Script.encode('utf-8','surrogateescape')
    raise ValueError(f'TextAsset nao encontrado em {bundle}')

def relocate(position, events):
    index=bisect.bisect_right(events,(position,10**18))-1
    return position+(events[index][1] if index>=0 else 0)

def main(raw,catalog,target,reference):
    blob=raw.read_bytes(); name_len=struct.unpack_from('<I',blob,0)[0]; start=4+name_len; start+=(4-start%4)%4
    script_len=struct.unpack_from('<I',blob,start)[0]; script_start=start+4; script=blob[script_start:script_start+script_len]
    if len(script)!=script_len: raise SystemExit('TextAsset .dat invalido')
    grouped=defaultdict(set)
    for r in csv.DictReader(catalog.open(encoding='utf-8',newline='')):
        if r['pt_br']: grouped[r['en']].add(r['pt_br'])
    mapping={k:next(iter(v)) for k,v in grouped.items() if len(v)==1}
    original_records=list(records(script, False)); arabic=get_script(reference); reference_records=list(records(arabic, False))
    if len(original_records)!=len(reference_records): raise SystemExit('Referencia estrutural incompativel')
    arab_events=[]
    for old,new in zip(original_records,reference_records):
        arab_events.append((old[3],new[3]-old[3]))
    out=bytearray(); cursor=0; changed=0; pt_events=[]; delta=0
    for source,length_at,end,table_end in original_records:
        value=mapping.get(source,source); encoded=value.encode('utf-8')
        out.extend(script[cursor:length_at]);out.extend(struct.pack('<I',len(encoded)));out.extend(encoded);cursor=end
        changed+=value!=source
        # Each table contains only the eight localized strings; after it, all
        # following offsets move by the accumulated size difference.
        old_table_len=table_end-(cursor-(8+len(encoded)))
        # derive its delta from the old English length at this record
        old_len=struct.unpack_from('<I',script,length_at)[0]
        delta += len(encoded)-old_len
        pt_events.append((table_end,delta))
    out.extend(script[cursor:])
    # Reference Arabic identifies fields that are true file offsets: their
    # values and their locations move according to the same table relocation.
    string_ranges=sorted((r[1],r[2]) for r in original_records)
    candidates=[]
    pos=0; range_index=0
    while pos<len(script)-3:
        while range_index<len(string_ranges) and string_ranges[range_index][1]<=pos:
            range_index+=1
        if range_index<len(string_ranges) and string_ranges[range_index][0]<=pos<string_ranges[range_index][1]:
            pos=string_ranges[range_index][1]
            continue
        ref_pos=relocate(pos,arab_events)
        if ref_pos+4>len(arabic):
            pos+=1
            continue
        value=struct.unpack_from('<I',script,pos)[0]
        if not 256<value<=len(script):
            pos+=1
            continue
        if struct.unpack_from('<I',arabic,ref_pos)[0] == relocate(value,arab_events):
            candidates.append(pos)
        pos+=1
    for pos in candidates:
        new_pos=relocate(pos,pt_events); value=struct.unpack_from('<I',script,pos)[0]
        struct.pack_into('<I',out,new_pos,relocate(value,pt_events))
    # Unity alinha strings para quatro bytes dentro do objeto serializado.
    # O original terminava alinhado; o texto PT-BR muda o tamanho total.
    padding=b'\0' * ((4-len(out)%4)%4)
    result=blob[:start]+struct.pack('<I',len(out))+bytes(out)+padding+blob[script_start+script_len:]
    target.write_bytes(result)
    print(f'Raw PT-BR: {target}; {changed} ocorrencias alteradas; {len(candidates)} offsets recalculados; {len(result)} bytes')

if __name__=='__main__': main(*(Path(x) for x in sys.argv[1:]))
