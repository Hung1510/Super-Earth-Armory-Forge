-- Super Earth Quad Drop (part of Super Earth Armory Forge 7.0)
-- Based on "HD2 Support Weapon Quad-Drop" 0.4.2 by Antigravity
-- https://ayakamods.com/mods/support-weapon-quad-drop.4660/  (permission: "Anyone is welcome to use,
-- modify, improve, redistribute, or build upon this mod. Please retain credit to all contributors.")
-- Needs HD2Runtime 0.28.1+ (skyeshade) and Bingus Shared Loader. Single-player / private lobbies only.
local key='SuperEarthQuadDropAddon'
if rawget(_G,key) then return rawget(_G,key) end
local state={version='@VERSION@',menu=false,runtime=false,operations={}}
rawset(_G,key,state)
local shared
pcall(function()
 local loader=rawget(_G,'CowboyBingusModLoader')
 if loader and type(loader.open_log)=='function' then shared=loader.open_log('SuperEarthQuadDrop.log') end
end)
local first=true
local function log(message)
 local line='[SuperEarthQuadDrop] '..tostring(message)
 pcall(function()
  if shared then shared:write(line..'\n');shared:flush()
  else
   local base=os.getenv('LOCALAPPDATA') or os.getenv('TEMP') or '.'
   local file=io.open(base..'/SuperEarthQuadDrop.log',first and 'w' or 'a')
   if file then file:write(line..'\n');file:close();first=false end
  end
 end)
 pcall(function()print(line)end)
end
log('Super Earth Quad Drop @VERSION@ entered (based on Quad-Drop 0.4.2 by Antigravity)')
local runtime,dependency_error
local ok,value=pcall(require,'mods/skyeshade/hd2runtime')
if ok then runtime=value else dependency_error=tostring(value);log('Runtime startup import failed: '..dependency_error) end

local backpack_choices={
 "B-1 Supply Pack",
 "SH-32 Shield Generator Pack",
 "LIFT-850 Jump Pack",
 "LIFT-860 Hover Pack",
 "LIFT-182 Warp Pack",
 "SH-20 Ballistic Shield Backpack",
 "SH-51 Directional Shield",
 "AX/AR-23 Guard Dog",
 "AX/LAS-5 Rover",
 "AX/TX-13 Dog Breath",
 "AX/ARC-3 K-9",
 "AX/FLAM-75 Hot Dog",
 "B-100 Portable Hellbomb",
 "None (Empty)"
}

local weapon_choices={
 "EAT-17 Expendable Anti-Tank",
 "MLS-4X Commando",
 "EAT-411 Leveller",
 "EAT-700 Expendable Napalm",
 "RS-422 Railgun",
 "LAS-99 Quasar Cannon",
 "M-105 Stalwart",
 "MG-43 Machine Gun",
 "MG-206 Heavy Machine Gun",
 "APW-1 Anti-Materiel Rifle",
 "GL-21 Grenade Launcher",
 "FLAM-40 Flamethrower",
 "ARC-3 Arc Thrower",
 "LAS-98 Laser Cannon",
 "None (Empty)"
}

local weapons_standard={
 {id="weapon_01",name="MG-43 Machine Gun",rack="pod-rack/v1/mg-43-machine-gun-pod/88639ae7ca41af2d",expect="pickup/v1/mg-43-machine-gun/7547c36fdd511b37",shared=true,default=1},
 {id="weapon_02",name="M-105 Stalwart",rack="pod-rack/v1/m-105-stalwart-pod/5df82aeb16072c40",expect="pickup/v1/m-105-stalwart/e173c48b267c2b90",shared=false,default=1},
 {id="weapon_03",name="MG-206 Heavy Machine Gun",rack="pod-rack/v1/mg-206-heavy-machine-gun-pod/91174b2ed6ccb6d1",expect="pickup/v1/mg-206-heavy-machine-gun-pod/7e824a240e1c41ae",shared=false,default=1},
 {id="weapon_04",name="APW-1 Anti-Materiel Rifle",rack="pod-rack/v1/apw-1-anti-materiel-rifle-pod/8dcbb503da441d61",expect="pickup/v1/apw-1-anti-materiel-rifle/3e89c8aedaec3cdb",shared=false,default=1},
 {id="weapon_05",name="RS-422 Railgun",rack="pod-rack/v1/rs-422-railgun-pod/54b39c863288fe57",expect="pickup/v1/rs-422-railgun/d0d22102ee2cf244",shared=false,default=1},
 {id="weapon_06",name="GL-21 Grenade Launcher",rack="pod-rack/v1/gl-21-grenade-launcher-pod/c55cfb6718aa8862",expect="pickup/v1/gl-21-grenade-launcher/879bce2fb521f366",shared=false,default=1},
 {id="weapon_07",name="GL-52 De-Escalator",rack="pod-rack/v1/gl-52-de-escalator-pod/58099e14803c613a",expect="empty",shared=false,default=1},
 {id="weapon_08",name="FLAM-40 Flamethrower",rack="pod-rack/v1/flam-40-flamethrower-pod/bcc672c4b42a0304",expect="pickup/v1/flam-40-flamethrower/b4d4c9c15a828fde",shared=false,default=1},
 {id="weapon_09",name="ARC-3 Arc Thrower",rack="pod-rack/v1/arc-3-arc-thrower-pod/8761f26c5ed582f5",expect="pickup/v1/arc-3-arc-thrower/ffb100733bda6a6c",shared=false,default=1},
 {id="weapon_10",name="LAS-98 Laser Cannon",rack="pod-rack/v1/las-98-laser-cannon-pod/52f9baecf22e0cee",expect="pickup/v1/las-98-laser-cannon/c6013cfe0815b790",shared=false,default=1},
 {id="weapon_11",name="LAS-99 Quasar Cannon",rack="pod-rack/v1/las-99-quasar-cannon-pod/b1ae155e0fa89340",expect="pickup/v1/las-99-quasar-cannon/ecf60a71601fe1ef",shared=false,default=2},
 {id="weapon_12",name="PLAS-45 Epoch",rack="pod-rack/v1/plas-45-epoch-pod/760fb0a30032e965",expect="pickup/v1/plas-45-epoch/f8f83fe309af696b",shared=false,default=1},
 {id="weapon_13",name="S-11 Speargun",rack="pod-rack/v1/s-11-speargun-pod/91993696dd106cb0",expect="pickup/v1/s-11-speargun/08be7186c997da64",shared=false,default=1},
 {id="weapon_14",name="40-K Meltagun",rack="pod-rack/v1/40-k-meltagun-pod/1e6cf1f42a6bff21",expect="empty",shared=false,default=1},
 {id="weapon_15",name="CQC-1 One True Flag",rack="pod-rack/v1/cqc-1-one-true-flag-pod/88379307961b6b81",expect="empty",shared=false,default=1},
 {id="weapon_16",name="CQC-20 Breaching Hammer",rack="pod-rack/v1/cqc-20-breaching-hammer-pod/4512a52513766018",expect="empty",shared=false,default=1},
 {id="weapon_17",name="CQC-9 Defoliation Tool",rack="pod-rack/v1/cqc-9-defoliation-tool-pod/c6ed955f2d984c15",expect="empty",shared=false,default=1},
}

local weapons_heavy={
 {id="weapon_18",name="AC-8 Autocannon",rack="pod-rack/v1/ac-8-autocannon-pod/b4ee7f86363c74a7",expect_s3="pickup/v1/ac-8-autocannon/58e7cf0743e30df4",expect_s4="pickup/v1/automatic-cannon-backpack/2c5bd6b88a4e6c81",shared=false,default_bp=2,default_gun=1},
 {id="weapon_19",name="GR-8 Recoilless Rifle",rack="pod-rack/v1/gr-8-recoilless-rifle-pod/18ca22d184369223",expect_s3="pickup/v1/gr-8-recoilless-rifle/c3681a5430f8eaa8",expect_s4="pickup/v1/recoilless-rifle-backpack/b2d8465b1b0ec213",shared=false,default_bp=2,default_gun=1},
 {id="weapon_20",name="FAF-14 SPEAR",rack="pod-rack/v1/faf-14-spear-pod/20071b627e68295f",expect_s3="pickup/v1/faf-14-spear/eedf1b3a064edb4b",expect_s4="pickup/v1/faf-missile-launcher-backpack/6cd4eb768919be66",shared=false,default_bp=2,default_gun=1},
 {id="weapon_21",name="RL-77 Airburst Rocket",rack="pod-rack/v1/rl-77-airburst-rocket-launcher-pod/bc171159d448ee1f",expect_s3="pickup/v1/rl-77-airburst-rocket-launcher/0eef82a268ed6eec",expect_s4="pickup/v1/air-burst-rocket-backpack/004ba933ad94ea53",shared=false,default_bp=2,default_gun=1},
 {id="weapon_22",name="M-1000 Maxigun",rack="pod-rack/v1/m-1000-maxigun-pod/01527a1b54e9452b",expect_s3="empty",expect_s4="empty",shared=false,default_bp=2,default_gun=1},
}

local DESC_SLOT1='Choose which backpack spawns on Bay 1 (Side Bay 1).'
local DESC_SLOT1_TOGGLE='Enable or disable Bay 1 (Side Bay 1) backpack spawn.'
local DESC_SLOT2='Choose which backpack spawns on Bay 2 (Side Bay 2).'
local DESC_SLOT2_TOGGLE='Enable or disable Bay 2 (Side Bay 2) backpack spawn.'
local DESC_SLOT3='Choose which extra support weapon spawns on Bay 3 (Opposite Bay).'
local DESC_SLOT3_TOGGLE='Enable or disable the Extra Support Weapon (Opposite Bay).'
local DESC_SUPPLY_TOGGLE='When enabled, spawns 1 real Supply Box in the opposite bay (replacing the Extra Gun). When disabled, the Extra Gun is restored.'

local rows={}

-- Category 1: Support Weapon Backpack 1
rows[#rows+1]={id='support_backpack_pairs.enabled',spec={type='toggle',label='Enable Bay 1 (Side Bay 1)',default=true,
 description=DESC_SLOT1_TOGGLE,mod='Support Weapon Backpack 1'}}
for _,w in ipairs(weapons_standard) do
 rows[#rows+1]={id='support_backpack_pairs.'..w.id,spec={type='choice',label=w.name,choices=backpack_choices,default=w.default,
  description=DESC_SLOT1,mod='Support Weapon Backpack 1'}}
end
for _,w in ipairs(weapons_heavy) do
 rows[#rows+1]={id='support_backpack_pairs.'..w.id,spec={type='choice',label=w.name,choices=backpack_choices,default=w.default_bp,
  description=DESC_SLOT1,mod='Support Weapon Backpack 1'}}
end

-- Category 2: Support Weapon Backpack 2
rows[#rows+1]={id='support_backpack_extra.enabled',spec={type='toggle',label='Enable Bay 2 (Side Bay 2)',default=true,
 description=DESC_SLOT2_TOGGLE,mod='Support Weapon Backpack 2'}}
for _,w in ipairs(weapons_standard) do
 rows[#rows+1]={id='support_backpack_extra.'..w.id,spec={type='choice',label=w.name,choices=backpack_choices,default=2,
  description=DESC_SLOT2,mod='Support Weapon Backpack 2'}}
end

-- Category 3: Support Weapon Extra Gun
rows[#rows+1]={id='support_backpack_gun.enabled',spec={type='toggle',label='Enable Extra Gun (Opposite Bay)',default=true,
 description=DESC_SLOT3_TOGGLE,mod='Support Weapon Extra Gun'}}
for _,w in ipairs(weapons_standard) do
 rows[#rows+1]={id='support_backpack_gun.'..w.id,spec={type='choice',label=w.name,choices=weapon_choices,default=1,
  description=DESC_SLOT3,mod='Support Weapon Extra Gun'}}
end
for _,w in ipairs(weapons_heavy) do
 rows[#rows+1]={id='support_backpack_gun.'..w.id,spec={type='choice',label=w.name,choices=weapon_choices,default=w.default_gun,
  description=DESC_SLOT3,mod='Support Weapon Extra Gun'}}
end

-- Category 4: Support Weapon Supply Box
rows[#rows+1]={id='support_supply_box.enabled',spec={type='toggle',label='Enable Supply Box Drop',default=true,
 description=DESC_SUPPLY_TOGGLE,mod='Support Weapon Supply Box'}}

local function register_menu()
 if state.menu then return true end
 local menu=rawget(_G,'ModOptionsMenu')
 if type(menu)~='table' or menu.api~=1 or type(menu.register_option)~='function' then return false end
 for _,row in ipairs(rows) do
  local success,result,reason=pcall(menu.register_option,row.id,row.spec)
  if not success or not result then
   state.error='Menu registration rejected '..row.id..': '..tostring(success and reason or result)
   log(state.error);state.menu_failed=true;return false
  end
 end
 state.menu=true;log('Menu registered: 4 categories with options')
 return true
end

local function safe_pickup(hd2, name)
 if name=='None (Empty)' or name=='empty' or name==nil then return 'empty' end
 if name=='Supply Box' then
  return hd2.pickup('pickup/v1/supply-box/d0e8fed8c01ceb1f')
 end
 if name=='MG-206 Heavy Machine Gun' then
  return hd2.pickup('pickup/v1/mg-206-heavy-machine-gun-pod/7e824a240e1c41ae')
 end
 local ok, res = pcall(hd2.pickup, name)
 if ok and res then return res end
 log('Warning: could not resolve pickup: '..tostring(name))
 return 'empty'
end

local function hook_slot(handle, get_fn, deps)
 local orig_get = handle.get
 handle.get = function(self)
  return get_fn(orig_get, self)
 end
 for _, dep in ipairs(deps) do
  if dep and type(dep.subscribe) == 'function' then
   dep:subscribe(function()
    for _, fn in ipairs(handle.listeners or {}) do
     pcall(fn)
    end
   end)
  end
 end
end

local function gameplay()
 local hd2=require('mods/skyeshade/hd2runtime')
 
 local options_1=hd2.options({id='support_backpack_pairs',title='Support Weapon Backpack 1',fallback='default'})
 local enabled_1=options_1:toggle({id='enabled',label='Enable Bay 1 (Side Bay 1)',default=true,
  description=DESC_SLOT1_TOGGLE})

 local options_2=hd2.options({id='support_backpack_extra',title='Support Weapon Backpack 2',fallback='default'})
 local enabled_2=options_2:toggle({id='enabled',label='Enable Bay 2 (Side Bay 2)',default=true,
  description=DESC_SLOT2_TOGGLE})

 local options_3=hd2.options({id='support_backpack_gun',title='Support Weapon Extra Gun',fallback='default'})
 local enabled_3=options_3:toggle({id='enabled',label='Enable Extra Gun (Opposite Bay)',default=true,
  description=DESC_SLOT3_TOGGLE})

 local options_supply=hd2.options({id='support_supply_box',title='Support Weapon Supply Box',fallback='default'})
 local supply_enabled=options_supply:toggle({id='enabled',label='Enable Supply Box Drop',default=true,
  description=DESC_SUPPLY_TOGGLE})

 local supply_pickup=safe_pickup(hd2, 'Supply Box')

 local backpack_values={}
 for i,name in ipairs(backpack_choices) do
  backpack_values[i]=safe_pickup(hd2, name)
 end

 local weapon_values={}
 for i,name in ipairs(weapon_choices) do
  weapon_values[i]=safe_pickup(hd2, name)
 end

 local operations={}

 -- 1. Standard weapons (17 weapons)
 for _,weapon in ipairs(weapons_standard) do
  local selected_1=options_1:choice({
   id=weapon.id,
   label=weapon.name,
   choices=backpack_choices,
   values=backpack_values,
   default=weapon.default,
   description=DESC_SLOT1
  })
  local selected_2=options_2:choice({
   id=weapon.id,
   label=weapon.name,
   choices=backpack_choices,
   values=backpack_values,
   default=2,
   description=DESC_SLOT2
  })
  local selected_3=options_3:choice({
   id=weapon.id,
   label=weapon.name,
   choices=weapon_choices,
   values=weapon_values,
   default=1,
   description=DESC_SLOT3
  })

  -- Slot 2 hook (Opposite Bay):
  -- When Supply Box is enabled: spawns Supply Box #1 (replaces Extra Gun)
  -- When Supply Box is disabled: spawns Extra Gun (if enabled)
  hook_slot(selected_3, function(orig, self)
   if supply_enabled:get() then
    return supply_pickup
   end
   if enabled_3:get() then
    return orig(self)
   end
   return 'empty'
  end, {supply_enabled, enabled_3})

  -- Slot 3 hook (Side Bay 1): Backpack 1 (always spawns cleanly!)
  hook_slot(selected_1, function(orig, self)
   if enabled_1:get() then
    return orig(self)
   end
   return 'empty'
  end, {enabled_1})

  -- Slot 4 hook (Side Bay 2): Backpack 2 (always spawns cleanly!)
  hook_slot(selected_2, function(orig, self)
   if enabled_2:get() then
    return orig(self)
   end
   return 'empty'
  end, {enabled_2})

  local rack=hd2.pod_rack(weapon.rack)
  local expected=weapon.expect=='empty' and 'empty' or safe_pickup(hd2, weapon.expect)

  operations[#operations+1]=hd2.ensure({
   interval=5,
   max_interval=60,
   plan={
    id='support-backpack-'..weapon.id,
    operations={
     {
      id='extra-gun-slot-2',
      target=rack:slot(2),
      field=hd2.fields.payload.entity,
      expect=expected,
      value=selected_3,
      allow_unverified_reference=true,
      allow_shared=weapon.shared
     },
     {
      id='backpack-slot-3',
      target=rack:slot(3),
      field=hd2.fields.payload.entity,
      expect='empty',
      value=selected_1,
      allow_unverified_reference=true,
      allow_shared=weapon.shared
     },
     {
      id='backpack-slot-4',
      target=rack:slot(4),
      field=hd2.fields.payload.entity,
      expect='empty',
      value=selected_2,
      allow_unverified_reference=true,
      allow_shared=weapon.shared
     },
     {
      id='four-items',
      target=rack,
      field=hd2.fields.payload.spawn_count,
      expect=1,
      value=4,
      allow_unverified_effect=true,
      allow_shared=weapon.shared
     },
    },
   }
  })
 end

 -- 2. Heavy weapons with native ammo pack (5 weapons)
 for _,weapon in ipairs(weapons_heavy) do
  local selected_bp=options_1:choice({
   id=weapon.id,
   label=weapon.name,
   choices=backpack_choices,
   values=backpack_values,
   default=weapon.default_bp,
   description=DESC_SLOT1
  })
  local selected_gun=options_3:choice({
   id=weapon.id,
   label=weapon.name,
   choices=weapon_choices,
   values=weapon_values,
   default=weapon.default_gun,
   description=DESC_SLOT3
  })

  -- Heavy Slot 3 hook:
  -- When Supply Box enabled: spawns Supply Box #1
  -- When Supply Box disabled: spawns Backpack 1 (if enabled)
  hook_slot(selected_bp, function(orig, self)
   if supply_enabled:get() then
    return supply_pickup
   end
   if enabled_1:get() then
    return orig(self)
   end
   return 'empty'
  end, {supply_enabled, enabled_1})

  -- Heavy Slot 4 hook:
  -- Extra Gun (if enabled)
  hook_slot(selected_gun, function(orig, self)
   if enabled_3:get() then
    return orig(self)
   end
   return 'empty'
  end, {enabled_3})

  local rack=hd2.pod_rack(weapon.rack)
  local exp_s3=weapon.expect_s3=='empty' and 'empty' or safe_pickup(hd2, weapon.expect_s3)
  local exp_s4=weapon.expect_s4=='empty' and 'empty' or safe_pickup(hd2, weapon.expect_s4)

  operations[#operations+1]=hd2.ensure({
   interval=5,
   max_interval=60,
   plan={
    id='support-backpack-'..weapon.id,
    operations={
     {
      id='backpack-slot-3',
      target=rack:slot(3),
      field=hd2.fields.payload.entity,
      expect=exp_s3,
      value=selected_bp,
      allow_unverified_reference=true,
      allow_shared=weapon.shared
     },
     {
      id='extra-gun-slot-4',
      target=rack:slot(4),
      field=hd2.fields.payload.entity,
      expect=exp_s4,
      value=selected_gun,
      allow_unverified_reference=true,
      allow_shared=weapon.shared
     },
     {
      id='four-items',
      target=rack,
      field=hd2.fields.payload.spawn_count,
      expect=2,
      value=4,
      allow_unverified_effect=true,
      allow_shared=weapon.shared
     },
    },
   }
  })
 end

 return operations
end

local runtime_attempted=false
local function start_runtime()
 if runtime_attempted or not state.menu then return end
 runtime=runtime or rawget(_G,'HD2RuntimeLibraryApi1')
 if type(runtime)~='table' then return end
 runtime_attempted=true
 local a,b,c=tostring(runtime.version):match('^(%d+)%.(%d+)%.(%d+)$')
 if runtime.api_version~=1 or not a or not (tonumber(a)>0 or tonumber(b)>28 or tonumber(b)==28 and tonumber(c)>=1) then
  state.error='Installed Runtime '..tostring(runtime.version)..' is incompatible; requires HD2Runtime 0.28.1+ / API 1'
  log(state.error);return
 end
 package.loaded['mods/skyeshade/hd2runtime']=runtime
 log('Starting gameplay with HD2Runtime '..tostring(runtime.version))
 local success,operations=pcall(gameplay)
 if not success then state.error='Gameplay setup failed: '..tostring(operations);log(state.error);return end
 state.operations=operations;state.runtime=true
 for i,operation in ipairs(operations) do
  if operation.status=='rejected' then log('Operation '..i..' rejected: '..tostring(operation.error)) end
 end
 log('22 quad-drop guarded operations registered (Supply Box + Backpacks + Extra Guns)')
end

local function tick()
 if not state.menu then register_menu() end
 if state.menu and not state.runtime then start_runtime() end
end

local loader=rawget(_G,'CowboyBingusModLoader')
if loader and type(loader.register_tick)=='function' then
 loader.register_tick(tick)
 log('Tick hook registered with CowboyBingusModLoader')
else
 tick()
end
return state
