-- ================================================================ tick and startup
local BUS = nil
local next_round, next_enforce = 0, 0

-- 7.3.5: what this mod itself costs per frame (the Mod Lag Watchdog counts "(+ all below it)": every
-- mod hooked underneath, so its figure is not this mod's alone). Written to ArmoryForge-STATUS.txt.
local COST = { t0 = nil, total = 0, frames = 0, worst = 0, worst_at = 0, over50 = 0, base_total = 0, base_worst = 0, chain = false }
state.cost = COST
local function cost_note(dt)
    COST.t0 = COST.t0 or api.now()
    COST.total, COST.frames = COST.total + dt, COST.frames + 1
    if dt > COST.worst then COST.worst, COST.worst_at = dt, state.frame end
    if dt > 0.05 then COST.over50 = COST.over50 + 1 end
end
function state.cost_lines()
    local span = COST.t0 and math.max(api.now() - COST.t0, 0.001) or 0
    local out = { '--- cost of this mod (its own update job) ---' }
    if COST.frames == 0 then out[#out + 1] = 'not measured yet'; return out end
    out[#out + 1] = string.format('own cost: %.2f ms/s average over %.0f s (%d frames), worst frame %.1f ms (frame %d), frames over 50 ms: %d',
        COST.total / span * 1000, span, COST.frames, COST.worst * 1000, COST.worst_at, COST.over50)
    if COST.chain then
        out[#out + 1] = string.format('everything below this hook (the game and the other mods hooked before it): %.1f ms/s average, worst %.0f ms',
            COST.base_total / span * 1000, COST.base_worst * 1000)
        out[#out + 1] = 'The Mod Lag Watchdog adds that to the line above, because it times this hook as "(+ all below it)".'
    end
    return out
end

local function tick_inner()
    state.frame = state.frame + 1
    if state.phase == 'gave_up' or state.frame < START_FRAME then return end
    local now = api.now()
    local wall = os.time()

    if state.phase == 'starting' then
        begin_round()
        state.phase = 'searching'
    elseif state.phase == 'searching' then
        local ok, finished = pcall(scan_step)
        if not ok then
            set_status('gave_up', 'scan error: ' .. tostring(finished))
            return
        end
        if finished then
            pcall(write_dump)          -- after every pass; only rewrites when something new was found
            if research then pcall(research.finish) end
            if good_enough() or state.rounds >= MAX_ROUNDS then
                set_status('ready', (complete() and 'all ' .. #CAT_LIST .. ' armor passives found'
                                     or ('found ' .. perks_found .. ' of ' .. #CAT_LIST .. ' armor passives'))
                                    .. '; ' .. summary())
                next_enforce = wall + ENFORCE_SECONDS
            else
                set_status('waiting', 'round ' .. state.rounds .. ': ' .. perks_found .. ' of ' .. #CAT_LIST .. ' armor passives found')
                next_round = wall + ROUND_DELAY_SECONDS
            end
        end
    elseif state.phase == 'waiting' then
        if wall >= next_round then
            begin_round()
            state.phase = 'searching'
        end
    elseif state.phase == 'ready' then
        if LOADOUT and not LOADOUT.retire and wall >= next_enforce then
            next_enforce = wall + ENFORCE_SECONDS
            local ok, gone = pcall(enforce)
            if ok and gone then
                state.rounds = 0
                begin_round()
                state.phase = 'searching'
            end
        end
    end

    if save_at and now >= save_at then pcall(save_now) end
    if research and research.tick and state.phase == 'ready' then pcall(research.tick, now) end
    if state.phase == 'ready' then
        local okw, why = pcall(KITS.wear_tick, now)
        if not okw then log('wearing: ' .. tostring(why)); KITS.wear.state, KITS.wear.tries = 'off', 99 end
    end
    if not MOD.no_panel then
        local ok, why = pcall(panel_tick, now)
        if not ok then log('panel: ' .. tostring(why)) end
    end
end

local function tick()
    local t0 = api.now()
    tick_inner()
    cost_note(api.now() - t0)
    if state.frame % 1800 == 0 and state.pp then state.pp.diag_dirty = true end   -- refresh the status file about every 30 s
end

-- ---------------------------------------------------------------- startup
local ok, failure = pcall(function()
    local loader = rawget(_G, 'CowboyBingusModLoader')
    assert(type(loader) == 'table' and type(loader.api) == 'number' and loader.api >= 1,
           'Bingus Shared Loader v15 or newer (API 1) is required')
    assert(ffi_ok and ffi, 'LuaJIT FFI is unavailable')
    assert(ffi.abi('64bit'), 'Windows x64 is required')
    assert(type(update) == 'function', 'the game update hook is unavailable')
    api = build_api()
    ensure_read_into()
    LOADOUT, state.loadout_source = load_loadout()
    self_addresses = { api.address_of(NEEDLE) }
    skip_low = (self_addresses[1] or LUA_HEAP_LIMIT) < LUA_HEAP_LIMIT
    if MOD.no_panel then
        log('panel: off in this build (panel = off); edit the loadout in the web builder')
    else
        setup_panel()
    end
end)

if not ok then
    state.phase, state.status = 'gave_up', tostring(failure)
    print('[' .. MOD.global .. '] ' .. tostring(failure))
    if api then pcall(flush_log) end
    return
end

-- for tests and other mods: read-only views of the live loadout
state.loadout = function() return LOADOUT end
state.resolve = resolve_profile
state.serialize = function() return serialize(LOADOUT, DEFAULT_KEY) end
state.changed = loadout_changed
state.kits = KITS

set_status('starting', 'waiting for the game to settle; ' .. state.loadout_source .. ' loadout')

BUS = rawget(_G, 'OCLAW_UPDATE_BUS')
if not BUS then
    BUS = { jobs = {}, base = update }
    if type(BUS.base) ~= 'function' then return end
    local dispatcher
    dispatcher = function(...)
        local b0 = api.now and api.now()
        local ok, first, second = pcall(BUS.base, ...)
        if b0 then
            local d = api.now() - b0
            COST.chain, COST.base_total = true, COST.base_total + d
            if d > COST.base_worst then COST.base_worst = d end
        end
        for _, job in pairs(BUS.jobs) do pcall(job) end
        if ok then return first, second end
    end
    BUS.dispatcher = dispatcher
    _G.OCLAW_UPDATE_BUS = BUS
    update = dispatcher
end
BUS.jobs[MOD.global] = tick
