-- CPU-only formatter/copy cases; no price RAM, money, actors or world edits.
local f=assert(io.open(assert(os.getenv('CN_INN_SEED')),'rb'));local seed=f:read('*a');f:close()
local cases=assert(dofile(assert(os.getenv('CN_INN_CASES'))))
local log=assert(io.open(assert(os.getenv('CN_INN_TRACE')),'w'))
local loaded=false;local active=false;local index=0;local sp0=0;local before=nil
local function rd(a)return emu.read(a,emu.memType.snesDebug)end
local function wr(a,v)emu.write(a,v,emu.memType.snesMemory)end
local function word(a)return rd(a)+256*rd(a+1)end
local function blob(a,n)local z={};for i=0,n-1 do z[#z+1]=string.char(rd(a+i))end;return table.concat(z)end
local function protected()return blob(0x7ef300,8)..blob(0x7ef31a,2)..blob(0x7ef320,224)..blob(0x7ef400,1024)..blob(0x7ef561,26*48)..blob(0x7ff960,33*48)end
local function nextTrial()
 index=index+1
 if index>#cases then log:write('RESULT completed='..#cases..' formatter_input_only=true no_draw=true\n');log:close();emu.stop(0);return end
 emu.loadSavestate(seed);before=protected();local c=cases[index];local s=emu.getState();sp0=s['cpu.sp']
 wr(0x7e0090,c.value&255);wr(0x7e0091,c.value>>8)
 for i=0,2 do wr(0x7e0078+i,(c.ptr>>(i*8))&255)end
 emu.setState({['cpu.k']=0xc0,['cpu.pc']=0x3391,['cpu.d']=0,['cpu.dbr']=0x7e,['cpu.ps']=s['cpu.ps']&0xcf})
 active=true
end
emu.addMemoryCallback(function()if not loaded then loaded=true;nextTrial()end end,emu.callbackType.exec,0xc0001c,0xc0001c,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 if not active then return end
 local s=emu.getState();local c=cases[index];assert(s['cpu.sp']==sp0 and protected()==before,'stack or world changed')
 local n=s['cpu.y'];assert(n==2 or n==4 or n==6,'bad copy length')
 local raw={};for i=0,n-1 do raw[#raw+1]=string.format('%02X',rd(0x7ed56d+i))end
 log:write(string.format('TRIAL idx=%d ptr=%06X amount=%d bytes=%d raw=%s A=%04X X=%04X Y=%04X SP=%04X D=%04X DB=%02X P=%02X protected=true\n',index,c.ptr,c.value,n,table.concat(raw,''),s['cpu.a'],s['cpu.x'],s['cpu.y'],s['cpu.sp'],s['cpu.d'],s['cpu.dbr'],s['cpu.ps']));log:flush()
 active=false;nextTrial()
end,emu.callbackType.exec,0xc03245,0xc03245,emu.cpuType.snes,emu.memType.snesMemory)
