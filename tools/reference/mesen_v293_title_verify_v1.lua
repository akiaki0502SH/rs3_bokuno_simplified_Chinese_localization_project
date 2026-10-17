-- Natural title boot. Observe adapters and glyphs without editing VM/world RAM.
local prefix=assert(os.getenv('CN_TITLE_PREFIX'))
local log=assert(io.open(prefix..'_trace.txt','w'))
local frame=0;local before=nil;local loopBefore=nil;local mapped=0;local glyphs=0;local originalReads=0
local pageStart=nil;local virtualCode=nil;local fontReads=0;local virtualGlyphs=0
local function rd(a)return emu.read(a,emu.memType.snesDebug)end
local function word(a)return rd(a)+256*rd(a+1)end
local function ptr()return word(0x7e0078)+65536*rd(0x7e007a)end
local function dump(name)
 local z={};for i=0,131071 do z[#z+1]=string.char(emu.read(i,emu.memType.snesWorkRam))end
 local f=assert(io.open(prefix..'_'..name..'.ram','wb'));f:write(table.concat(z));f:close()
end
local function shot(name)local f=assert(io.open(prefix..'_'..name..'.png','wb'));f:write(emu.takeScreenshot());f:close()end
emu.addMemoryCallback(function()
 before=emu.getState()
 log:write(string.format('GETTER f=%d ptr=%06X end=%04X SP=%04X\n',frame,ptr(),word(0x7e007b),before['cpu.sp']));log:flush()
end,emu.callbackType.exec,0x3ffc54,0x3ffc54,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not before then return end
 local after=emu.getState()
 for _,key in ipairs({'a','x','y','d','dbr','ps'})do assert(before['cpu.'..key]==after['cpu.'..key],'getter ABI '..key)end
 assert(after['cpu.sp']==before['cpu.sp']+3,'getter SP')
 if rd(0x7e007a)==0x59 or rd(0x7e007a)==0x3f then mapped=mapped+1;pageStart=frame end
 log:write(string.format('ADAPTED f=%d ptr=%06X end=%04X ABI=true\n',frame,ptr(),word(0x7e007b)));log:flush();before=nil
end,emu.callbackType.exec,0xff38e9,0xff38e9,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 loopBefore=emu.getState();loopBefore.titlePtr=ptr();loopBefore.titleEnd=word(0x7e007b)
end,emu.callbackType.exec,0x3ffcc0,0x3ffcc0,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not loopBefore then return end
 local after=emu.getState()
 for _,key in ipairs({'x','y','d','dbr','sp'})do assert(loopBefore['cpu.'..key]==after['cpu.'..key],'loop ABI '..key)end
 assert((loopBefore['cpu.ps']&0x5d)==(after['cpu.ps']&0x5d),'loop preserved status')
 if ptr()~=loopBefore.titlePtr then
  log:write(string.format('RESTORED f=%d old=%06X ptr=%06X end=%04X ABI=true\n',frame,loopBefore.titlePtr,ptr(),word(0x7e007b)));log:flush()
 end
 loopBefore=nil
end,emu.callbackType.exec,0xff3975,0xff3975,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if virtualCode then assert(fontReads==30,'virtual glyph must fetch 15 complete rows')end
 glyphs=glyphs+1
 fontReads=0;virtualCode=rd(0x7eeff6)==1 and word(0x7e008d)or nil
 if virtualCode then virtualGlyphs=virtualGlyphs+1 end
 log:write(string.format('GLYPH f=%d ptr=%06X code=%04X map=%04X tile=%04X\n',frame,ptr(),word(0x7e008d),word(0x7ed5c2),word(0x7ed51b)));log:flush()
end,emu.callbackType.exec,0xff39ee,0xff39ee,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a)
 assert(virtualCode,'virtual font fetched without a virtual title character')
 local slot=(virtualCode-0x2800)&0x7ff
 local top=0x780000+(slot//8)*256+(slot%8)*16
 assert((a>=top and a<top+16)or(a>=top+128 and a<top+144),'wrong virtual glyph address')
 fontReads=fontReads+1
end,emu.callbackType.read,0x780000,0x78ffff,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()originalReads=originalReads+1 end,emu.callbackType.read,0xfc0937,0xfc0bd3,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()return 0 end,emu.callbackType.read,0x4218,0x4219,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 frame=frame+1
 if pageStart and frame-pageStart==120 then shot('page'..mapped);dump('page'..mapped)end
 for _,f in ipairs({1200,3000,4600,5800,6500})do
  if frame==f then shot(string.format('f%05d',frame));dump(string.format('f%05d',frame))end
 end
 if frame==6500 then
  if virtualCode then assert(fontReads==30,'last virtual glyph fetch count')end
  log:write(string.format('RESULT mapped_pages=%d glyphs=%d virtual_glyphs=%d original_text_reads=%d no_VM_or_world_writes=true\n',mapped,glyphs,virtualGlyphs,originalReads));log:close();emu.stop(mapped==4 and glyphs>300 and 0 or 1)
 end
end,emu.eventType.startFrame)
