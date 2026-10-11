"""Center two environment headings and align 阳 components, on frozen v28405."""
from pathlib import Path
import hashlib,json,sys
from PIL import ImageDraw
from build_v284_display_feedback_v1 import unpack
from build_font_payloads import encode_pixels
from build_v283_missing_translations_v1 import atoms
from dry_run_encoding_plan import encode
P=Path(__file__).resolve().parents[1]
rd=lambda f:json.loads((P/f).read_text(encoding='utf8'))
sha=lambda z:hashlib.sha256(z).hexdigest().upper()

def main():
 out=(P/sys.argv[1]).resolve();proof=(P/sys.argv[2]).resolve();independent=len(sys.argv)>3 and sys.argv[3]=='independent'
 assert out.is_relative_to(P)and proof.is_relative_to(P)and not out.exists()and not proof.exists()
 manifest=rd('text/translations/translation_sources_before_v285_20261011_01.json');assert manifest['build_revision']=='v284_display_feedback05'
 basefile=manifest['latest_test_ROM']['file'];b=(P/basefile).read_bytes();assert sha(b)=='1AE9BC0CDE210C2957D817D085C91B4BEBF60E6455C708523B8D6D9C2EFF02D3'
 r=bytearray(b);allow=bytearray(len(b));writes=[]
 mapping={k:bytes.fromhex(v)for k,v in rd(manifest['latest_font_mapping']).items()}
 def enc(text):
  z,miss,err=encode(text,mapping,battle=False);assert not miss and not err;return z
 def put(at,data,why):
  r[at:at+len(data)]=data;allow[at:at+len(data)]=b'\1'*len(data)
  writes.append({'offset':f'{at:06X}','bytes':len(data),'before_hex':b[at:at+len(data)].hex(' ').upper(),'after_hex':data.hex(' ').upper(),'reason':why})
 # Keep all cache positions and control code intact; only move blank cells.
 sound_at=0x3DBA74;speed_at=0x3DBB00
 assert b[sound_at:sound_at+6]==enc('声音')+b'\x50'*2
 assert b[speed_at:speed_at+18]==enc('菜单光标速度')+b'\x50'*6
 sound=b'\x50'+enc('声音')+b'\x50';speed=b'\x50'*3+enc('菜单光标速度')+b'\x50'*3
 assert len(sound)==6 and len(atoms(sound))==4 and len(speed)==18 and len(atoms(speed))==12
 put(sound_at,sound,'center 声音 in original four cached cells')
 put(speed_at,speed,'center 菜单光标速度 in original twelve cached cells')
 code=mapping['阳'];assert code==bytes.fromhex('11 C0')
 slot=256+code[1];off=slot//8*256+slot%8*16
 before=b[0x780000+off:0x780010+off]+b[0x780080+off:0x780090+off]
 im=unpack(before);left=im.crop((0,0,7,16));bbox=left.getbbox();assert bbox==(3,3,7,14)
 for y in range(16):
  for x in range(7,16):im.putpixel((x,y),0)
 top,bottom=bbox[1],bbox[3]-1
 draw=ImageDraw.Draw(im);draw.rectangle((7,top,12,bottom),outline=1);draw.line((7,(top+bottom)//2,12,(top+bottom)//2),fill=1)
 assert list(left.getdata())==list(im.crop((0,0,7,16)).getdata())
 assert im.crop((7,0,16,16)).getbbox()[1::2]==bbox[1::2]
 glyph=encode_pixels(im);assert glyph!=before
 for base in [0x780000,0x7D0000]:
  assert b[base+off:base+off+16]+b[base+off+128:base+off+144]==before
  put(base+off,glyph[:16],'阳 日 matches left radical top and bottom, upper')
  put(base+off+128,glyph[16:],'阳 日 matches left radical top and bottom, lower')
 assert r[0x5BA000:0x5BBA00]==b[0x5BA000:0x5BBA00]
 assert r[0x50000:0x60000]==b[0x50000:0x60000]and r[0x7F0000:0x800000]==b[0x7F0000:0x800000]
 assert r[0x7FFE00:0x7FFFF0]==bytes(496)
 for at in [0xFFDC,0x40FFDC]:
  r[at:at+4]=bytes.fromhex('FF FF 00 00');allow[at:at+4]=b'\1'*4
 checksum=sum(r)&65535
 for at in [0xFFDC,0x40FFDC]:r[at:at+4]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
 assert len(r)==0x800000 and sum(r)&65535==checksum and all(allow[i]for i,(a,c)in enumerate(zip(b,r))if a!=c)
 for x in writes:
  at=int(x['offset'],16);assert r[at:at+x['bytes']]==bytes.fromhex(x['after_hex'])
 out.write_bytes(r)
 report={'schema':'v285-center-and-yang-build-v1','status':'STATIC_READBACK_PASS_RUNTIME_PENDING','ROM':out.relative_to(P).as_posix(),'SHA256':sha(r),'base_ROM':basefile,'base_SHA256':sha(b),'writes':writes,'headings':{'声音':{'offset':f'{sound_at:06X}','cells':4,'left_blank_cells':1,'right_blank_cells':1},'菜单光标速度':{'offset':f'{speed_at:06X}','cells':12,'left_blank_cells':3,'right_blank_cells':3}},'yang_glyph':{'code':'11 C0','left_bbox':list(bbox),'right_bbox':[7,top,13,bottom+1],'new_hex':glyph.hex(' ').upper(),'old_SHA256':sha(before),'new_SHA256':sha(glyph),'same_top_and_bottom':True,'left_radical_unchanged':True,'right_width_unchanged':True,'right_height_before':12,'right_height_after':bottom-top+1},'all_native_code_and_prior_fixes_preserved':True,'reserved496_preserved':True,'formal_baseline_promoted':False}
 proof.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 if not independent:
  tag=proof.stem.rsplit('_',1)[1]
  overlay=P/f'text/translations/display_feedback_v285_20261011_{tag}.json';assert not overlay.exists()
  overlay.write_text(json.dumps({'schema':'v285-display-overlay-v1','base_manifest':'text/translations/translation_sources_before_v285_20261011_01.json','ROM_SHA256':sha(r),'headings':report['headings'],'yang_glyph':report['yang_glyph']},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  mp=P/f'qa/V285_CURRENT_SINGLE_GLYPH_MAPPING_20261011_{tag}.json';assert not mp.exists();mp.write_bytes((P/manifest['latest_font_mapping']).read_bytes())
  fontdir=(P/f'font/v285_feedback_20261011_{tag}').resolve();assert fontdir.is_relative_to(P)and not fontdir.exists();fontdir.mkdir()
  atlas=rd(manifest['latest_font_atlas'])
  for key,base in [('eventAtlas',0x780000),('fixedAtlas',0x7D0000)]:
   oldfile=P/atlas[key]['path'];data=r[base:base+oldfile.stat().st_size];newfile=fontdir/oldfile.name;newfile.write_bytes(data)
   atlas[key]={'path':newfile.relative_to(P).as_posix(),'sha256':sha(data)}
  entries=[x for x in atlas['glyphs']if x['atom']=='阳']
  assert len(entries)==1;entries[0]['glyphSha256']=sha(glyph);entries[0]['source']='v285_yang_component_alignment'
  atlas.update(source_version='v285_center_and_yang'+tag,final_ROM_SHA256=sha(r));atlas['notes'].append('v285阳的右日上下边缘与左耳旁一致，均从y3到y13共11像素；其他字形保持。')
  af=P/f'docs/SINGLE_GLYPH_ATLAS_V285_FEEDBACK_20261011_{tag}.json';assert not af.exists();af.write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:report[k]for k in ['ROM','SHA256','headings','yang_glyph']},ensure_ascii=False))

if __name__=='__main__':sys.stdout.reconfigure(encoding='utf8');main()
