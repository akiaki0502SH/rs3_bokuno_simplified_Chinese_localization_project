#!/usr/bin/env python3
"""Build 16x16 1bpp font payloads and an atlas; never writes a ROM."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dry_run_encoding_plan import base_encoding
from render_font_candidates import pixels_16x16_1bpp_tiles
STD=0x2C0000;EXT=0x608000;CHINESE_STD=0x284000;CHINESE_EXT=0x780000;PAGES=0x782000
def interleaved_base(slot):return (slot//8)*0x100+(slot%8)*0x10
def read_interleaved(data,base,slot):
 start=base+interleaved_base(slot)
 return data[start:start+16]+data[start+0x80:start+0x90]
def write_interleaved(data,slot,glyph):
 start=interleaved_base(slot);data[start:start+16]=glyph[:16];data[start+0x80:start+0x90]=glyph[16:32]
def source_glyph(data,code):
 if len(code)==1 and 0x51<=code[0]<=0xFF:return read_interleaved(data,STD,code[0]-0x50)
 if len(code)==2 and 0x20<=code[0]<=0x23:return read_interleaved(data,STD,(code[0]-0x20)*256+code[1])
 if len(code)==2 and code[0]==0x18:return read_interleaved(data,EXT,code[1])
 return None
def encode_pixels(img):
 out=bytearray(32)
 for y in range(16):
  for x in range(16):
   if img.getpixel((x,y)):
    i=((y//8)*2+(x//8))*8+(y%8);out[i]|=1<<(7-(x%8))
 return bytes(out)
def render_char(ch,font,smallfont):
 im=Image.new('L',(16,16),0);d=ImageDraw.Draw(im)
 if len(ch)>1:
  for i,c in enumerate(ch[:2]):
   box=d.textbbox((0,0),c,font=smallfont);w=box[2]-box[0];h=box[3]-box[1];d.text((i*8+(8-w)//2-box[0],(16-h)//2-box[1]-1),c,font=smallfont,fill=255)
 else:
  box=d.textbbox((0,0),ch,font=font);w=box[2]-box[0];h=box[3]-box[1];x=(16-w)//2-box[0];y=(16-h)//2-box[1]-1;d.text((x,y),ch,font=font,fill=255,stroke_width=0)
 return im.point(lambda p:255 if p>=96 else 0).convert('1')
def cht_glyph(ch,reference,base,count):
 if reference is None or len(ch)!=1:return None
 try:encoded=ch.encode('gb2312')
 except UnicodeEncodeError:return None
 if len(encoded)!=2 or not (0xB0<=encoded[0]<=0xFF and 0xA1<=encoded[1]<=0xFE):return None
 index=(encoded[0]-0xB0)*94+(encoded[1]-0xA1)
 if index<0 or index>=count:return None
 start=base+interleaved_base(index);glyph=reference[start:start+16]+reference[start+0x80:start+0x90]
 return glyph if len(glyph)==32 else None
def hzk12_glyph(ch,data):
 if data is None or len(ch)!=1:return None
 try:encoded=ch.encode('gb2312')
 except UnicodeEncodeError:return None
 if len(encoded)!=2 or not (0xA1<=encoded[0]<=0xF7 and 0xA1<=encoded[1]<=0xFE):return None
 index=(encoded[0]-0xA1)*94+(encoded[1]-0xA1);start=index*24;raw=data[start:start+24]
 if len(raw)!=24:return None
 im=Image.new('1',(16,16),0)
 for y in range(12):
  for x in range(12):
   if raw[y*2+x//8]&(0x80>>(x%8)):im.putpixel((x+2,y+2),1)
 return encode_pixels(im)
def is_cjk(ch):
 return len(ch)==1 and (0x3400<=ord(ch)<=0x9FFF or 0xF900<=ord(ch)<=0xFAFF)
def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--allocation',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--cht-rom',type=Path);p.add_argument('--cht-base',type=lambda value:int(value,0),default=0x2C0200);p.add_argument('--cht-count',type=int,default=1024);p.add_argument('--hzk12',type=Path);p.add_argument('--uniform-cjk',action='store_true');p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();rom=a.rom.read_bytes();g=json.loads(a.allocation.read_text(encoding='utf-8'));out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);fallback_size=12 if a.hzk12 else 14;pair_size=7 if a.hzk12 else 8;font=ImageFont.truetype(str(a.font),fallback_size,index=0);smallfont=ImageFont.truetype(str(a.font),pair_size,index=0);reference=a.cht_rom.resolve().read_bytes() if a.cht_rom else None;hzk=a.hzk12.resolve().read_bytes() if a.hzk12 else None
 prefixes=[int(x[-2:],16) for x in g.get('extension_prefixes',['18F0','18F1','18F2','18F3'])];std=bytearray(rom[STD:STD+0x8000]);ext=bytearray(rom[EXT:EXT+0x2000]);pages=bytearray(len(prefixes)*0x2000);fixed_atlas=bytearray(len(prefixes)*0x2000);source=base_encoding();copied=rendered=reference_used=hzk_used=0;glyph_images=[]
 for item in g['allocation']:
  ch=item['character'];code=bytes.fromhex(item['code']);src=source_glyph(rom,source.get(ch,b''));reference_glyph=cht_glyph(ch,reference,a.cht_base,a.cht_count);bitmap_glyph=hzk12_glyph(ch,hzk)
  if bitmap_glyph is not None:glyph=bitmap_glyph;hzk_used+=1
  elif a.uniform_cjk and is_cjk(ch):glyph=encode_pixels(render_char(ch,font,smallfont));rendered+=1
  elif reference_glyph is not None:glyph=reference_glyph;reference_used+=1
  elif src is not None:glyph=src;copied+=1
  else:glyph=encode_pixels(render_char(ch,font,smallfont));rendered+=1
  if len(code)==1:write_interleaved(std,code[0]-0x50,glyph)
  elif len(code)==2 and 0x20<=code[0]<=0x23:write_interleaved(std,(code[0]-0x20)*256+code[1],glyph)
  elif len(code)==2 and code[0]==0x18:write_interleaved(ext,code[1],glyph)
  else:target=(prefixes.index(code[1])*256+code[2])*32;pages[target:target+32]=glyph
  if item.get('fixed_code'):
   fc=bytes.fromhex(item['fixed_code']);slot=(fc[0]-0x10)*256+fc[1];base=(slot//8)*0x100+(slot%8)*0x10;fixed_atlas[base:base+16]=glyph[:16];fixed_atlas[base+0x80:base+0x90]=glyph[16:32]
  glyph_images.append((ch,glyph))
 payloads=[]
 preserved=g.get('phase')=='preserved_source_glyph_allocation';hybrid=g.get('phase')=='hybrid_glyph_allocation'
 payload_defs=([('standard_font',STD,std)] if a.uniform_cjk else [])+[('extension_pages',0x780000,pages),('fixed_renderer_atlas',0x7D0000,fixed_atlas)] if preserved else ([('standard_font',STD,std),('extended_18xx_font',EXT,ext),('extension_pages_4',0x284000,pages)] if hybrid else [('compact_standard_font',CHINESE_STD,std),('compact_extended_18xx_font',CHINESE_EXT,ext),('extension_pages_4',PAGES,pages)])
 for name,offset,data in payload_defs:
  fn=name+'.bin';(out/fn).write_bytes(data);payloads.append({'name':name,'offset':f'0x{offset:06X}','length':len(data),'file':fn,'sha256':hashlib.sha256(data).hexdigest().upper()})
 supporting_artifacts=[]
 if not any(name=='extended_18xx_font' for name,_,_ in payload_defs):
  fn='extended_18xx_font.bin';(out/fn).write_bytes(ext);supporting_artifacts.append({'name':fn,'length':len(ext),'file':fn,'sha256':hashlib.sha256(ext).hexdigest().upper(),'rom_write':False})
 cols=32;rows=(len(glyph_images)+cols-1)//cols;atlas=Image.new('RGB',(cols*18,rows*18),'#20242b')
 for i,(ch,raw) in enumerate(glyph_images):
  px=pixels_16x16_1bpp_tiles(raw);ox=(i%cols)*18;oy=(i//cols)*18
  for y,row in enumerate(px):
   for x,v in enumerate(row):
    if v:atlas.putpixel((ox+x,oy+y),(255,255,255))
 atlas.save(out/'final_font_atlas.png')
 r={'phase':'font_payloads','rom_write_performed':False,'font_source':str(a.font.resolve()),'fallback_font_size':fallback_size,'fallback_pair_font_size':pair_size,'uniform_cjk':a.uniform_cjk,'hzk12_source':str(a.hzk12.resolve()) if a.hzk12 else None,'hzk12_glyphs_used':hzk_used,'cht_reference_rom':str(a.cht_rom.resolve()) if a.cht_rom else None,'cht_reference_base':f'0x{a.cht_base:06X}' if a.cht_rom else None,'cht_reference_count':a.cht_count if a.cht_rom else 0,'cht_reference_glyphs_used':reference_used,'copied_source_glyphs':copied,'rendered_new_glyphs':rendered,'payloads':payloads,'supporting_artifacts':supporting_artifacts,'atlas':'final_font_atlas.png','runtime_mode':'preserved_original_plus_fixed_2byte' if preserved else ('hybrid_reserved_ui' if hybrid else 'dual_font'),'extension_region':f'0x780000-0x{0x780000+len(pages)-1:06X}' if preserved else ('0x284000-0x28BFFF' if hybrid else '0x782000-0x789FFF')}
 a.manifest.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(r,ensure_ascii=False))
if __name__=='__main__':main()
