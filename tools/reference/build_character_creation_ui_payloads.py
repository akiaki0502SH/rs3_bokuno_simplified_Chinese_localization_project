#!/usr/bin/env python3
"""Build fixed-size Chinese payloads for the previously unindexed character-creation UI block."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dry_run_encoding_plan import encode
FIELDS=[
 ('character_heading_suffix',0x3DFAB7,8,'性角色'),
 ('label_name',0x3DFAC3,3,'名'),
 ('label_sex',0x3DFAC6,4,'性别'),
 ('label_identity',0x3DFACA,3,'身'),
 ('label_star',0x3DFACD,4,'宿星'),
 ('prompt_sex',0x3DFAD1,14,'请选择性别'),
 ('prompt_protagonist',0x3DFADF,14,'请选择主角'),
 ('prompt_star',0x3DFBAD,16,'请选择宿星'),
 ('prompt_weapon',0x3DFBBD,18,'请选择武器'),
 ('prompt_confirm',0x3DFBCF,9,'确定？'),
 ('choice_yes',0x3DFBDB,2,'是'),
 ('choice_no',0x3DFBDD,3,'否'),
 ('status_technique_suffix',0x3DF857,2,'术'),
 ('status_sex',0x3DF87C,4,'性别'),
 ('status_dexterity',0x3DF882,4,'灵巧'),
 ('status_speed',0x3DF886,4,'速度'),
 ('status_japanese_suffix',0x3DF895,1,' '),
 ('creation_weapon_sword',0x3DF91A,2,'剑'),
 ('creation_weapon_skill_suffix',0x3DF91C,2,'术'),
 ('creation_weapon_spear',0x3DF927,2,'枪'),
 ('creation_weapon_martial',0x3DF92B,4,'体术'),
 ('button_word',0x3DFBE1,3,'按'),
 ('weapon_sword',0x3DFBFC,6,'剑术'),
 ('weapon_greatsword',0x3DFC02,6,'大剑术'),
 ('weapon_axe',0x3DFC08,6,'斧术'),
 ('weapon_club',0x3DFC0E,7,'棍棒术'),
 ('weapon_rapier',0x3DFC15,7,'小剑术'),
 ('weapon_spear',0x3DFC1C,6,'枪术'),
 ('weapon_bow',0x3DFC22,6,'弓术'),
 ('weapon_martial',0x3DFC28,6,'体术'),
 ('prologue_title',0x684300,32,'开场：死蚀威胁'),
]
def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--allocation',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();rom=a.rom.read_bytes();g=json.loads(a.allocation.read_text(encoding='utf-8'));out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);mapping={' ':b'\x50'}
 for x in g['allocation']:
  if x.get('class')!='composite_pair':mapping[x['character']]=bytes.fromhex(x.get('fixed_code') or x['code'])
 compressed=dict(mapping)
 for x in g['allocation']:
  if x.get('fixed_code'):compressed[x['character']]=bytes.fromhex(x['fixed_code'])
 writes=[];errors=[]
 for name,offset,capacity,text in FIELDS:
  data,missing,token_errors=encode(text,mapping,battle=False)
  if not missing and not token_errors and len(data)>capacity:data,missing,token_errors=encode(text,compressed,battle=False)
  if missing or token_errors or len(data)>capacity:errors.append({'name':name,'text':text,'length':len(data),'capacity':capacity,'missing':sorted(missing),'tokens':token_errors});continue
  payload=data+b'\x50'*(capacity-len(data));fn=name+'.bin';(out/fn).write_bytes(payload);writes.append({'name':name,'offset':f'0x{offset:06X}','length':capacity,'file':fn,'expected':rom[offset:offset+capacity].hex(' ').upper(),'sha256':hashlib.sha256(payload).hexdigest().upper(),'text':text})
 report={'phase':'character_creation_ui_payloads','rom_write_performed':False,'writes':writes,'errors':errors};a.manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'writes':len(writes),'errors':errors},ensure_ascii=False))
 if errors:raise SystemExit(2)
if __name__=='__main__':main()
