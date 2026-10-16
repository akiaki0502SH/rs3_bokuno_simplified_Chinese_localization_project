-- Isolated native-window smoke. Original source window entry, synthetic VM
-- metadata only, no source ROM edits; not an original story/actor replay.
local seedFile=assert(io.open(assert(os.getenv('CN_V291_SEED')),'rb'))
local seed=seedFile:read('*a');seedFile:close()
local case=assert(dofile(assert(os.getenv('CN_V291_CASE'))))
local trace=assert(io.open(assert(os.getenv('CN_V291_OUT'))..'_trace.txt','w'))
local loaded=false;local injected=false;local frames=0;local startFrame=0
local readerHits=0;local newReads=0;local before=nil;local injectHook=nil
local function rd(a)return emu.read(a,emu.memType.snesDebug)end
local function wr(a,v)emu.write(a,v,emu.memType.snesMemory)end
local function ptr()return rd(0x7e0078)+256*rd(0x7e0079)+65536*rd(0x7e007a)end
local function blob(a,n)local s={};for i=0,n-1 do s[#s+1]=string.char(rd(a+i))end;return table.concat(s)end
local function protection()return blob(0x7ef400,1024)..blob(0x7ef561,26*48)..blob(0x7ff960,33*48)..blob(0x7ef300,8)..blob(0x7ef31a,2)..blob(0x7ef320,224)end
emu.addMemoryCallback(function()
 if loaded then return end;loaded=true;emu.loadSavestate(seed);startFrame=frames
 trace:write('LOADED controlled_window=true original_story_replay=false\n');trace:flush()
end,emu.callbackType.exec,0xc0001c,0xc0001c,emu.cpuType.snes,emu.memType.snesMemory)
injectHook=emu.addMemoryCallback(function()
 if not loaded or injected or frames-startFrame<2 then return end
 local st=emu.getState();if st['cpu.d']~=0 or rd(0x7e0076)~=0 then return end
 before=protection();local beforeFile=assert(io.open(os.getenv('CN_V291_OUT')..'_before.ram','wb'));beforeFile:write(blob(0x7e0000,131072));beforeFile:close();injected=true;startFrame=frames
 local at=case.anchor-1
 for i=0,2 do wr(0x7e0078+i,(at>>(8*i))&255)end
 wr(0x7e007b,0xfe);wr(0x7e007c,0xff);wr(0x7e0077,0);wr(0x7ed599,case.mode);wr(0x7e0076,1)
 trace:write(string.format('INJECT anchor=%06X target=%06X expected=%dx%d\n',case.anchor,case.target,case.cols,case.rows));trace:flush()
 emu.removeMemoryCallback(injectHook,emu.callbackType.exec,0xc00000,0xc0ffff,emu.cpuType.snes,emu.memType.snesMemory)
end,emu.callbackType.exec,0xc00000,0xc0ffff,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not injected then return end
 local at=ptr();if at>=case.target and at<case.target+case.bytes then readerHits=readerHits+1 end
end,emu.callbackType.exec,0xc01bc6,0xc01bc6,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if injected then newReads=newReads+1 end
end,emu.callbackType.read,case.target,case.target+case.bytes-1,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()return 0 end,emu.callbackType.read,0x4218,0x4219,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 frames=frames+1
 if injected and frames-startFrame==300 then
  local f=assert(io.open(os.getenv('CN_V291_OUT')..'.png','wb'));f:write(emu.takeScreenshot());f:close()
  local index=rd(0x7ed5a5)+256*rd(0x7ed5a6);local cols=rd(0x7ed5c0+index);local rows=rd(0x7ed5c1+index)
  local same=protection()==before
  local ramFile=assert(io.open(os.getenv('CN_V291_OUT')..'_after.ram','wb'));ramFile:write(blob(0x7e0000,131072));ramFile:close()
  trace:write(string.format('RESULT reader_hits=%d new_ROM_reads=%d cols=%d rows=%d protected=%s cursor=%06X active=%02X\n',readerHits,newReads,cols,rows,tostring(same),ptr(),rd(0x7e0076)));trace:flush();trace:close()
  -- Opening a window itself may change native fields. Protection must be
  -- checked against the baseline ROM under the same fixture, not idle RAM.
  emu.stop(readerHits>0 and newReads>0 and cols==case.cols and rows==case.rows and 0 or 1)
 elseif frames>800 then trace:write('TIMEOUT injected='..tostring(injected)..'\n');trace:close();emu.stop(1)end
end,emu.eventType.startFrame)
