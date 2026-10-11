#!/usr/bin/env python3
"""Build the 18 F0-F3 xx four-page font renderer hook; never writes a ROM."""
import argparse,hashlib,json
from pathlib import Path
SOURCE_SHA='4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0'
def branch_code(parts):
 out=bytearray();labels={};fix=[]
 for item in parts:
  if isinstance(item,tuple) and item[0]=='label':labels[item[1]]=len(out)
  elif isinstance(item,tuple):out.append(item[1]);fix.append((len(out),item[2]));out.append(0)
  else:out.extend(bytes.fromhex(item))
 for pos,label in fix:
  delta=labels[label]-(pos+1)
  if not -128<=delta<=127:raise ValueError('branch range')
  out[pos]=delta&0xFF
 return bytes(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();rom=a.rom.read_bytes();sha=hashlib.sha256(rom).hexdigest().upper();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
 if sha!=SOURCE_SHA:raise SystemExit('source hash mismatch')
 writes=[]
 def save(name,offset,cpu,data,expected=None):
  if expected is not None and rom[offset:offset+len(expected)]!=expected:raise SystemExit(f'{name} signature mismatch')
  if expected is None and any(x!=0xFF for x in rom[offset:offset+len(data)]):raise SystemExit(f'{name} target not FF')
  fn=name+'.bin';(out/fn).write_bytes(data);writes.append({'name':name,'offset':f'0x{offset:06X}','cpu_address':cpu,'length':len(data),'file':fn,'expected':expected.hex(' ').upper() if expected else 'FF fill','sha256':hashlib.sha256(data).hexdigest().upper()})
 save('font_index_hook',0x59E009,'0x59E009',bytes.fromhex('5C 80 DA 59'),bytes.fromhex('EB 22 00 E1'))
 helper=branch_code(['48','5A','EB','29 FF 00','C9 F0 00',(None,0x90,'fallback'),'C9 F4 00',(None,0xB0,'fallback'),'38','E9 F0 00','EB','0A','0A','0A','0A','0A','85 90','A0 02 00','B7 78','29 FF 00','0A','0A','0A','0A','0A','18','65 90','85 90','E6 78','7A','68','A5 90','48','E2 20','A9 02','8F F6 EF 7E','C2 20','68','64 90','6B',('label','fallback'),'7A','68','48','E2 20','AF F6 EF 7E','C9 02',(None,0xD0,'keepmode'),'A9 01','8F F6 EF 7E',('label','keepmode'),'C2 20','68','EB','22 00 E1 59','5C 0E E0 59'])
 save('font_index_helper',0x59DA80,'0x59DA80',helper)
 for i in range(8):
  hook=0x59E01A+i*0x10;stub=0x59DB00+i*0x40;save(f'font_reader_hook_{i}',hook,f'0x{hook:06X}',bytes((0x5C,stub&0xFF,(stub>>8)&0xFF,(stub>>16)&0xFF)),bytes.fromhex('E0 FF 7F 90'))
  off=i
  body=branch_code(['AF F6 EF 7E',(None,0xF0,'old'),'C9 02',(None,0xF0,'pages'),'E0 FF 7F',(None,0x90,'cnstd'),f'BF {off:02X} 80 77','6B',('label','cnstd'),f'BF {off:02X} 40 E8','6B',('label','pages'),f'BF {off:02X} 20 78','6B',('label','old'),'E0 FF 7F',(None,0x90,'std'),f'BF {off:02X} 00 60','6B',('label','std'),f'BF {off:02X} 00 EC','6B'])
  save(f'font_reader_helper_{i}',stub,f'0x{stub:06X}',body)
 mode=branch_code(['08','E2 20','A5 7A','C9 69',(None,0xF0,'cn'),'C9 76',(None,0xF0,'cn'),'C9 77',(None,0xF0,'cn'),'C9 FD',(None,0xF0,'fd'),'C9 5A',(None,0xD0,'old'),'C2 20','A5 78','C9 00 2D',(None,0x90,'old16'),'C9 00 36',(None,0xB0,'old16'),(None,0x80,'cn16'),('label','fd'),'C2 20','A5 78','C9 00 A8',(None,0x90,'cn16'),('label','old16'),'E2 20',('label','old'),'A9 00',(None,0x80,'store'),('label','cn16'),'E2 20',('label','cn'),'A9 01',('label','store'),'8F F6 EF 7E','28','A7 78','22 00 E1 59','5C 06 D4 55'])
 save('font_mode_hook',0x55D400,'0x55D400',bytes.fromhex('5C 00 DD 59'),bytes.fromhex('A7 78 22 00'))
 save('font_mode_helper',0x59DD00,'0x59DD00',mode)
 fixedmode=branch_code(['08','E2 20','A5 77','C9 69',(None,0xF0,'cn'),'C9 76',(None,0xF0,'cn'),'C9 77',(None,0xF0,'cn'),'C9 FD',(None,0xF0,'fd'),'C9 5A',(None,0xD0,'old'),'C2 20','A5 75','C9 00 2D',(None,0x90,'old16'),'C9 00 36',(None,0xB0,'old16'),(None,0x80,'cn16'),('label','fd'),'C2 20','A5 75','C9 00 A8',(None,0x90,'cn16'),('label','old16'),'E2 20',('label','old'),'A9 00',(None,0x80,'store'),('label','cn16'),'E2 20',('label','cn'),'A9 01',('label','store'),'8F F6 EF 7E','28','C2 20','A0 00 00','5C 35 DE C5'])
 save('fixed_renderer_mode_hook',0x05DE30,'0xC5DE30',bytes.fromhex('5C 60 DD 59'),bytes.fromhex('C2 20 A0 00'))
 save('fixed_renderer_mode_helper',0x59DD60,'0x59DD60',fixedmode)
 r={'phase':'font_renderer_hook','rom_write_performed':False,'source_sha256':sha,'escape_format':'18 F0-F3 XX','mode_flag':'0x7EEFF6 (0=original,1=compact Chinese,2=extension page)','writes':writes};a.manifest.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'writes':len(writes),'index_helper_bytes':len(helper),'mode_helper_bytes':len(mode)},ensure_ascii=False))
if __name__=='__main__':main()
