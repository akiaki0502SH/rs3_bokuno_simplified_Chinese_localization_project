-- Display-only reproduction: select a native result window, no progression edits.
local f=assert(io.open(assert(os.getenv('CN_V292_SEED')),'rb'));local seed=f:read('*a');f:close()
local prefix=assert(os.getenv('CN_V292_PREFIX'))
local case=assert(dofile(assert(os.getenv('CN_V292_CASE'))))
local log=assert(io.open(prefix..'_trace.txt','w'))
local loaded,held,done=false,false,false
local frames,sp0=0,0
local function rd(a)return emu.read(a,emu.memType.snesDebug)end
local function wr(a,v)emu.write(a,v,emu.memType.snesMemory)end
local function word(a)return rd(a)+256*rd(a+1)end
local function dump(name)
 local z={};for i=0,131071 do z[#z+1]=string.char(emu.read(i,emu.memType.snesWorkRam))end
 local o=assert(io.open(prefix..'_'..name..'.ram','wb'));o:write(table.concat(z));o:close()
end
local function shot(name)local o=assert(io.open(prefix..'_'..name..'.png','wb'));o:write(emu.takeScreenshot());o:close()end
emu.addMemoryCallback(function()
 if loaded then return end;loaded=true;emu.loadSavestate(seed)
 local st=emu.getState();local d=0x7e0000+st['cpu.d'];sp0=st['cpu.sp']
 assert(st['cpu.d']==0x900 and st['cpu.dbr']==0x7e and(st['cpu.ps']&0x30)==0x20)
 dump('initial')
 wr(d+0x3d,case.id or 0)
 if case.amount then
  local str=tostring(case.amount);wr(d+0x1a,#str)
  for i=1,#str do wr(0x7e09d8-#str+i,tonumber(str:sub(i,i)))end
  local p=0x09d9-#str;wr(d+0xaa,p&255);wr(d+0xab,p>>8);wr(d+0xac,0)
 end
 emu.setState({['cpu.k']=0xc2,['cpu.pc']=case.entry})
 log:write(string.format('CASE entry=C2%04X id=%d amount=%d SP=%04X display_only=true\n',case.entry,case.id or 0,case.amount or 0,sp0));log:flush()
end,emu.callbackType.exec,0xc0001c,0xc0001c,emu.cpuType.snes,emu.memType.snesMemory)
for _,pc in ipairs({0xfeaada,0xfeabfa,0xfeb64c})do
 emu.addMemoryCallback(function()
  if not loaded or done then return end
  local st=emu.getState();local d=0x7e0000+st['cpu.d'];local ptr=word(d+0xaa)+65536*rd(d+0xac)
  local n=pc==0xfeabfa and rd(d+0x1a)or rd(d+0x4b)
  if pc==0xfeb64c then n=word(d+0x8a)end
  local raw={};for i=0,math.min(n,32)-1 do raw[#raw+1]=string.format('%02X',rd(ptr+i))end
  log:write(string.format('%s f=%d ptr=%06X n=%d ui=%02X indexed=%s x=%d y=%d width=%d height=%d raw=%s\n',pc==0xfeb64c and'LENGTH'or pc==0xfeabfa and'NUMBER'or'DRAW',frames,ptr,n,rd(d+0x65),tostring((rd(d+0x1e)&0x10)~=0),rd(d+0x7e),rd(d+0x7f),rd(d+0x80),rd(d+0x7d),table.concat(raw,' ')));log:flush()
 end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,emu.memType.snesMemory)
end
emu.addMemoryCallback(function()
 if not loaded or done then return end;local st=emu.getState();local d=0x7e0000+st['cpu.d']
 log:write(string.format('GLYPH code=%02X%02X x=%d y=%d frameX=%d frameY=%d width=%d height=%d\n',rd(d+0x63),rd(d+0x62),rd(d+0x72),rd(d+0x73),rd(d+0x7a),rd(d+0x7b),rd(d+0x80),rd(d+0x7d)));log:flush()
end,emu.callbackType.exec,0xfeac41,0xfeac41,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not loaded or done then return end
 if not held then
  held=true;log:write(string.format('DRAW_DONE SP=%04X baseline=%04X\n',emu.getState()['cpu.sp'],sp0));log:flush()
  emu.setState({['cpu.k']=0x3f,['cpu.pc']=0xf280})
 else
  done=true;shot('visible');dump('final')
  log:write(string.format('RESULT native_return=true SP_before=%04X SP_after=%04X frames=%d\n',sp0,emu.getState()['cpu.sp'],frames));log:close();emu.stop(0)
 end
end,emu.callbackType.exec,0xc20000+case.finish,0xc20000+case.finish,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()return 0 end,emu.callbackType.read,0x4218,0x4219,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 frames=frames+1
 if loaded and not done and frames>600 then done=true;log:write('TIMEOUT\n');log:close();shot('timeout');emu.stop(1)end
end,emu.eventType.startFrame)
