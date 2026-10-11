from pathlib import Path
import ctypes as C,sys,json,gzip,hashlib,os
from PIL import Image
# libretro ABI: https://raw.githubusercontent.com/libretro/RetroArch/master/libretro-common/include/libretro.h
P=Path.cwd().resolve();assert P.is_relative_to(Path('G:/CodexProjects'));corepath=Path('E:/RetroArch/cores/snes9x_libretro.dll');rompath=Path(sys.argv[1]).resolve();statepath=Path(sys.argv[2]).resolve();steps=json.loads(Path(sys.argv[3]).read_text(encoding='utf-8-sig'));prefix=(P/sys.argv[4]).resolve();assert prefix.is_relative_to(P)and not prefix.with_suffix('.json').exists();assert statepath.is_relative_to(P/'user_saves')or statepath.is_relative_to(P/'qa')or statepath.is_relative_to(P/'artifacts/private_human_tests');sha=lambda b:hashlib.sha256(b).hexdigest().upper()
class Game(C.Structure):_fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Info(C.Structure):_fields_=[('name',C.c_char_p),('version',C.c_char_p),('extensions',C.c_char_p),('need_fullpath',C.c_bool),('block_extract',C.c_bool)]
class Var(C.Structure):_fields_=[('key',C.c_char_p),('value',C.c_char_p)]
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p);VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t);AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16);BATCH=C.CFUNCTYPE(C.c_size_t,C.POINTER(C.c_int16),C.c_size_t);POLL=C.CFUNCTYPE(None);INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
lib=C.CDLL(str(corepath));pixel=2;screen=None;mask=0;frame=0;envdir=str(prefix.parent).encode('utf-8');option_values={};callbacks=[]
def env(cmd,data):
 global pixel
 cmd=cmd&0xffff
 if cmd==10:pixel=C.cast(data,C.POINTER(C.c_int)).contents.value;return pixel in[0,1,2]
 if cmd in[9,30,31]:C.cast(data,C.POINTER(C.c_char_p))[0]=envdir;return True
 if cmd==15:
  q=C.cast(data,C.POINTER(Var)).contents
  if q.key in option_values:q.value=option_values[q.key];return True
  return False
 if cmd==16:
  arr=C.cast(data,C.POINTER(Var));i=0
  while arr[i].key:
   val=arr[i].value
   if val and b'; 'in val:option_values[arr[i].key]=val.split(b'; ',1)[1].split(b'|',1)[0]
   i+=1
  return True
 if cmd==17:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
 if cmd in[18,11]:return True
 if cmd==3:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
 if cmd==27:return False  # optional variadic logging interface unavailable
 if cmd==47:
  if data:C.cast(data,C.POINTER(C.c_uint))[0]=3
  return True
 return False
def video(data,w,h,pitch):
 global screen
 if not data or data==C.c_void_p(-1).value:return
 import numpy as np
 raw=C.string_at(data,pitch*h)
 if pixel==1:
  a=np.frombuffer(raw,dtype=np.uint32).reshape(h,pitch//4)[:,:w];rgb=np.stack([(a>>16)&255,(a>>8)&255,a&255],axis=-1).astype('uint8')
 else:
  a=np.frombuffer(raw,dtype=np.uint16).reshape(h,pitch//2)[:,:w];g=(a>>5)&(63 if pixel==2 else 31);r=(a>>(11 if pixel==2 else 10))&31;b=a&31;rgb=np.stack([(r*255//31),g*255//(63 if pixel==2 else 31),b*255//31],axis=-1).astype('uint8')
 screen=Image.fromarray(rgb.copy())
def inputstate(port,device,index,id):return int(port==0 and device==1 and id<16 and (mask>>id)&1)
for name,typ,func in [('environment',ENV,env),('video_refresh',VIDEO,video),('audio_sample',AUDIO,lambda l,r:None),('audio_sample_batch',BATCH,lambda data,n:n),('input_poll',POLL,lambda:None),('input_state',INPUT,inputstate)]:
 cb=typ(func);callbacks.append(cb);setter=getattr(lib,'retro_set_'+name);setter.argtypes=[typ];setter.restype=None;setter(cb)
lib.retro_api_version.restype=C.c_uint;assert lib.retro_api_version()==1;lib.retro_get_system_info.argtypes=[C.POINTER(Info)];info=Info();lib.retro_get_system_info(C.byref(info));assert not info.need_fullpath
lib.retro_init.restype=None;lib.retro_init();rom=rompath.read_bytes();rbuf=C.create_string_buffer(rom);game=Game(str(rompath).encode('utf-8'),C.cast(rbuf,C.c_void_p),len(rom),None);lib.retro_load_game.argtypes=[C.POINTER(Game)];lib.retro_load_game.restype=C.c_bool;assert lib.retro_load_game(C.byref(game)),'ROM load failed';lib.retro_set_controller_port_device.argtypes=[C.c_uint,C.c_uint];lib.retro_set_controller_port_device(0,1)
lib.retro_get_memory_size.argtypes=[C.c_uint];lib.retro_get_memory_size.restype=C.c_size_t;lib.retro_get_memory_data.argtypes=[C.c_uint];lib.retro_get_memory_data.restype=C.c_void_p
lib.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];lib.retro_unserialize.restype=C.c_bool;rawstate=statepath.read_bytes();state=gzip.decompress(rawstate)if rawstate[:2]==b'\x1f\x8b'else rawstate;sbuf=C.create_string_buffer(state);assert lib.retro_unserialize(sbuf,len(state)),'Snes9x snapshot rejected';assert lib.retro_get_memory_size(2)==131072
initial=C.string_at(lib.retro_get_memory_data(2),131072);Path(str(prefix)+'_before.ram').write_bytes(initial)
vm=[]; ram_hashes=[]
buttons=['B','Y','SELECT','START','UP','DOWN','LEFT','RIGHT','A','X','L','R'];lib.retro_run.restype=None
for step,(keys,hold,wait)in enumerate(steps):
 for active,n in[(True,hold),(False,wait)]:
  mask=sum(1<<buttons.index(k)for k in keys)if active else 0
  for _ in range(n):
   lib.retro_run();frame+=1; current=C.string_at(lib.retro_get_memory_data(2),131072);vm.append(current[0x78:0x7b].hex());ram_hashes.append(sha(current))
 if screen is not None:screen.save(str(prefix)+f'_step{step:03d}.png')
Path(str(prefix)+'.vm').write_text('\n'.join(vm));Path(str(prefix)+'.wram_hashes.json').write_text(json.dumps(ram_hashes));ram=C.string_at(lib.retro_get_memory_data(2),131072);sramlen=lib.retro_get_memory_size(0);sram=C.string_at(lib.retro_get_memory_data(0),sramlen)if sramlen else b'';Path(str(prefix)+'.ram').write_bytes(ram);Path(str(prefix)+'.srm').write_bytes(sram)
lib.retro_serialize_size.restype=C.c_size_t;size=lib.retro_serialize_size();buf=C.create_string_buffer(size);lib.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];lib.retro_serialize.restype=C.c_bool;assert lib.retro_serialize(buf,size);Path(str(prefix)+'.state').write_bytes(buf.raw)
if screen is not None:screen.save(str(prefix)+'.png')
def ids(lo,n):return[r for r in range(n)if ram[lo+48*r]!=255]
result={'status':'NORMAL_INPUT_RUN_COMPLETED_REQUIRES_REVIEW','ROM':str(rompath),'ROM_SHA':sha(rom),'state':str(statepath),'state_SHA':sha(rawstate),'snapshot_header':state[:14].decode(errors='replace'),'core':str(corepath),'core_SHA':sha(corepath.read_bytes()),'core_name':info.name.decode(),'core_version':info.version.decode(),'frames':frame,'steps':steps,'WRAM_SHA':sha(ram),'SRAM_bytes':sramlen,'native26_occupied':ids(0xf561,26),'extended33_occupied':ids(0x1f960,33),'slot27':ram[0x1fe70:0x1fea0].hex(),'loaded_user_state_no_VM_world_writes':True};Path(str(prefix)+'.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding='utf-8');print(json.dumps(result,ensure_ascii=False));lib.retro_unload_game();lib.retro_deinit()
