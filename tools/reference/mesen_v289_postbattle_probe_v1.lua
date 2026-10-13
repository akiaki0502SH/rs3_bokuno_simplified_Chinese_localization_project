-- Controlled post-battle display metadata only. No item, skill, actor or world injection.
local seed=assert(io.open(assert(os.getenv('CN_REWARD_SEED')),'rb')):read('*a')
local prefix=assert(os.getenv('CN_REWARD_PREFIX'))
local kind=os.getenv('CN_REWARD_KIND')or'inspect'
local id=tonumber(os.getenv('CN_REWARD_ID')or'15')
local special=os.getenv('CN_REWARD_SPECIAL')=='1'
local destroyed=os.getenv('CN_REWARD_DESTROYED')=='1'
local extended=os.getenv('CN_REWARD_EXTENDED')=='1'
local log=assert(io.open(prefix..'_trace.txt','w'))
local loaded,held,done=false,false,false
local frames,sp0=0,0
local returnSite=kind=='item'and 0xc2ceea or 0xc2d14a
local function read(a)return emu.read(a,emu.memType.snesDebug)end
local function write(a,v)emu.write(a,v,emu.memType.snesMemory)end
local function word(a)return read(a)+256*read(a+1)end
local function dump(name)
 local data={};for i=0,131071 do data[#data+1]=string.char(emu.read(i,emu.memType.snesWorkRam))end
 local f=assert(io.open(prefix..'_'..name..'.ram','wb'));f:write(table.concat(data));f:close()
end
local function shot(name)local f=assert(io.open(prefix..'_'..name..'.png','wb'));f:write(emu.takeScreenshot());f:close()end
emu.addMemoryCallback(function()
 if loaded then return end;loaded=true;emu.loadSavestate(seed)
 local st=emu.getState();local d=0x7e0000+st['cpu.d'];sp0=st['cpu.sp']
 log:write(string.format('SEED D=%04X DB=%02X SP=%04X P=%02X A=%04X X=%04X Y=%04X pc=%02X%04X\n',st['cpu.d'],st['cpu.dbr'],sp0,st['cpu.ps'],st['cpu.a'],st['cpu.x'],st['cpu.y'],st['cpu.k'],st['cpu.pc']))
 for _,off in ipairs({0x1c,0x1e,0x22,0x3c,0x42,0x46,0x4b,0x65,0x7a,0x7b,0x7d,0x7e,0x7f,0x80,0x82,0xaa,0xac,0xff})do
  log:write(string.format('PARAM %02X=%02X\n',off,read(d+off)))
 end
 dump('initial')
 if kind=='inspect'then log:close();emu.stop(0);return end
 assert(st['cpu.d']==0x900 and st['cpu.dbr']==0x7e and(st['cpu.ps']&0x30)==0x20)
 write(d+0x42,id);write(d+0x3c,read(d+0x3c)&0x3f)
 if kind=='item'then
  write(d+0x46,id);write(d+0xff,extended and 1 or 0)
  write(d+0x1c,read(d+0x1c)&0xfd)
  if destroyed then write(d+0x1c,read(d+0x1c)|2)end
  emu.setState({['cpu.k']=0xc2,['cpu.pc']=0xce72})
 else
  if special then write(d+0x3c,read(d+0x3c)|0x40)end
  emu.setState({['cpu.k']=0xc2,['cpu.pc']=0xd0d4})
 end
 log:write(string.format('CONTROLLED_DISPLAY kind=%s id=%02X special=%s no_world_actor_inventory_skill_writes=true\n',kind,id,tostring(special)));log:flush()
end,emu.callbackType.exec,0xc0001c,0xc0001c,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not loaded or done then return end;local st=emu.getState();local d=0x7e0000+st['cpu.d'];local ptr=word(d+0xaa)+65536*read(d+0xac)
 local limit=read(d+0x4b);local indexed=(read(d+0x1e)&0x10)~=0
 if indexed then limit=word(0x3f9fd0+read(d+0x65)*2)end
 local raw={};for i=0,math.min(limit,64)-1 do raw[#raw+1]=string.format('%02X',read(ptr+i))end
 log:write(string.format('DRAW f=%d ptr=%06X len=%d ui=%02X indexed=%s x=%d y=%d width=%d height=%d raw=%s\n',frames,ptr,limit,read(d+0x65),tostring(indexed),read(d+0x7e),read(d+0x7f),read(d+0x80),read(d+0x7d),table.concat(raw,' ')));log:flush()
end,emu.callbackType.exec,0xfeaada,0xfeaada,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not loaded or done then return end;local st=emu.getState();local d=0x7e0000+st['cpu.d']
 log:write(string.format('GLYPH f=%d high=%02X low=%02X x=%d y=%d frameX=%d frameY=%d width=%d height=%d\n',frames,read(d+0x63),read(d+0x62),read(d+0x72),read(d+0x73),read(d+0x7a),read(d+0x7b),read(d+0x80),read(d+0x7d)));log:flush()
end,emu.callbackType.exec,0xfeac41,0xfeac41,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not loaded or done then return end
 if not held then
  held=true;log:write(string.format('NATIVE_DRAW_DONE SP=%04X baseline=%04X\n',emu.getState()['cpu.sp'],sp0));log:flush()
  emu.setState({['cpu.k']=0x3f,['cpu.pc']=0xf280})
 else
  done=true;shot('visible');dump('final')
  log:write(string.format('RESULT native_return=true SP_before=%04X SP_after=%04X frames=%d controlled_display_only=true\n',sp0,emu.getState()['cpu.sp'],frames));log:close();emu.stop(0)
 end
end,emu.callbackType.exec,returnSite,returnSite,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a)
 if loaded and(a==0x4218)and frames%80<2 then return 0x80 end;return 0
end,emu.callbackType.read,0x4218,0x4219,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 frames=frames+1
 if loaded and not done and frames>600 then done=true;log:write('RESULT timeout=true\n');log:close();shot('timeout');emu.stop(1)end
end,emu.eventType.startFrame)
