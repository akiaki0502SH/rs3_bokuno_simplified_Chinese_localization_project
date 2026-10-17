local prefix=assert(os.getenv('CN_TITLE_PREFIX'))
local log=assert(io.open(prefix..'_trace.txt','w'))
local frame=0;local seen={};local reads=0;local normal=0
local function rd(a)return emu.read(a,emu.memType.snesDebug)end
local function pc()local s=emu.getState();return s['cpu.k']*65536+s['cpu.pc']end
local function ptr()return rd(0x7e0078)+256*rd(0x7e0079)+65536*rd(0x7e007a)end
emu.addMemoryCallback(function(a,v)
 reads=reads+1;local p=pc();local key=string.format('%06X:%06X',p,a)
 if not seen[key]then seen[key]=true;local st=emu.getState();log:write(string.format('NATIVE f=%d pc=%06X addr=%06X value=%02X vm=%06X D=%04X DB=%02X X=%04X Y=%04X\n',frame,p,a,v,ptr(),st['cpu.d'],st['cpu.dbr'],st['cpu.x'],st['cpu.y']));log:flush()end
end,emu.callbackType.read,0xfc0937,0xfc0bd3,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 normal=normal+1
 if normal<40 then log:write(string.format('NORMAL f=%d vm=%06X\n',frame,ptr()));log:flush()end
end,emu.callbackType.exec,0xc01bc6,0xc01bc6,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()return 0 end,emu.callbackType.read,0x4218,0x4219,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 frame=frame+1
 for _,f in ipairs({120,300,600,900,1200,1800,2400,3000,3600,4800,6000})do
  if frame==f then local o=assert(io.open(prefix..string.format('_f%05d.png',frame),'wb'));o:write(emu.takeScreenshot());o:close();log:write(string.format('FRAME f=%d pc=%06X vm=%06X native_reads=%d normal=%d\n',frame,pc(),ptr(),reads,normal));log:flush()end
 end
 if frame==6000 then log:write('DONE no_world_or_VM_writes=true\n');log:close();emu.stop(0)end
end,emu.eventType.startFrame)
