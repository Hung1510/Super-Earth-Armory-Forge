-- ================================================================ stratagem presets
-- The Stratagems tab: save the four stratagems on the Hellpod loadout screen as a named preset and put a
-- saved one back with a click. It uses the game's own calls: the slot widget setter, the slots-changed
-- refresh and the loadout save, the same ones the Clear Stratagems key of Flexible Stratagems uses.
--
-- How the game's loadout code is found (byte signatures, at this build's addresses first, else a search of
-- game.dll over a few frames), the screen and slot layout, and the native calls come from the research notes and
-- the mod "Flexible Stratagems" by Alomare (https://github.com/Alomare/FlexibleStratagems, NOTES.md).
-- Credit to Alomare. The search engine below is written for this mod.
-- Nothing runs until the Stratagems tab is opened. Anything not found, found twice or inconsistent turns the
-- feature off and the loadout screen works as normal.
local STRAT = (function()
local SIGS = {
    {name = 'screen', rva = 0x1082ef0, text = '48 8B 05 ?? ?? ?? ?? 48 8B 88 ?? ?? ?? ?? 83 B9 ?? ?? ?? ?? FF 0F 95 C0 C3',
     fields = {stack = {'rip', {3}, {7}}, slot = {'u32', {10}}, local_index = {'u32', {16}}}},
    {name = 'refresh_a', rva = 0x18d194f, text = '41 39 8C 24 ?? ?? ?? ?? 76 ?? 0F 1F 80 00 00 00 00 8B C1 FF C1 42 C6 84 20 ?? ?? ?? ?? 01 41 3B 8C 24 ?? ?? ?? ?? 72 ?? 45 39 BD ?? ?? ?? ?? 0F 86 ?? ?? ?? ?? 48 8D 1D ?? ?? ?? ?? 48 8D 3D ?? ?? ?? ?? 0F 1F 40 00 66 66 0F 1F 84 00 00 00 00 00 4B 8D 0C 7F 48 03 C9 41 8B 84 CD ?? ?? ?? ?? 85 C0 75 ?? 48 8B C3 EB ?? 48 8B 04 C7 44 8B 58 04 45 85 DB 74 ??',
     fields = {list_count = {'u32', {4, 34}}, selectable = {'u32', {25}}, block_count = {'u32', {43}}, strat_table = {'rip', {63}, {67}}, block_entries = {'u32', {92}}}},
    {name = 'refresh_b', rva = 0x18d19c5, text = '4C 8B 0D ?? ?? ?? ?? 41 8B 91 ?? ?? ?? ?? 45 8B 91 ?? ?? ?? ?? 41 3B D2 73 ?? 4D 8D 81 ?? ?? ?? ?? 4D 8D 04 90 66 0F 1F 44 00 00 41 8B 00 48 8D 0C 40 49 8D 81 ?? ?? ?? ?? 44 39 5C C8 08 48 8D 04 C8 74 ?? FF C2 49 83 C0 04 41 3B D2 72 ?? EB ?? 48 85 C0 74 ?? 8B 50 04 45 33 C0 49 8B CC E8 ?? ?? ?? ??',
     fields = {offers = {'rip', {3}, {7}}, first = {'u32', {10}}, last = {'u32', {17}}, indices = {'u32', {29}}, entries = {'u32', {53}}, mark = {'call', {96}, {100}}}},
    {name = 'offers_count', rva = 0x146e1cf, text = '4C 8B 1D ?? ?? ?? ?? 85 D2 74 ?? 45 8B 83 ?? ?? ?? ?? 8B CE 45 85 C0 74 ?? 49 8D 83 ?? ?? ?? ??',
     fields = {offers = {'rip', {3}, {7}}, offers_count = {'u32', {14}}, entries = {'u32', {28}}}},
    {name = 'kind_frv', rva = 0x146e2e0, text = '49 8B 0A 39 41 04 74 ?? 41 FF C0 49 83 C2 08 41 81 F8 ?? ?? ?? ?? 72 ?? 44 8B C6 48 8B C3 4C 8B DE EB ?? 44 8B C1 45 8B D8 4B 8B 04 DE F7 80 ?? ?? ?? ?? 00 00 20 00',
     fields = {types = {'u32', {18}}, flags = {'u32', {47}}}},
    {name = 'ready_toggle', rva = 0x189c4d0, text = '4C 8B 05 ?? ?? ?? ?? 8B 87 ?? ?? ?? ?? 45 8B 90 ?? ?? ?? ?? 45 85 D2 74 ?? 4D 8D 88 ?? ?? ?? ?? 49 81 C0 ?? ?? ?? ?? 49 8B 08 39 41 08 74 ?? 83 FB FF 74 ?? 41 8B 11 8B CA C1 E9 03 80 E1 01 75 ?? C1 EA 0B 80 E2 01 74 ?? FF C3 49 83 C0 08 49 83 C1 20 41 3B DA 72 ?? B3 01 80 BF ?? ?? ?? ?? 00 0F 84 ?? ?? ?? ?? F3 0F 10 87 ?? ?? ?? ?? 0F 2E 05 ?? ?? ?? ?? 7A ?? 75 ?? 32 C0 EB ?? 32 DB EB ?? 8B 97 FC ED 01 00 0F 57 DB 41 B8 63 19 1D 5D F3 0F 11 5C 24 20 E8 ?? ?? ?? ?? 48 8B 15 ?? ?? ?? ?? C7 87 ?? ?? ?? ?? ?? ?? ?? ?? 83 BA ?? ?? ?? ?? 01 72 ?? 48 8B 8A ?? ?? ?? ?? F6 41 14 01 74 ?? 83 A2 ?? ?? ?? ?? F7 BA 01 05 0F F5 E8 ?? ?? ?? ?? 48 8B B4 24 F8 00 00 00 B8 04 00 00 00 48 81 C4 D8 00 00 00 5F 5B C3 8B D0 E8 ?? ?? ?? ?? 8B 97 FC ED 01 00 84 C0 75 ?? 0F 57 DB 41 B8 A4 50 E1 97 F3 0F 11 5C 24 20 E8 ?? ?? ?? ?? C7 87 ?? ?? ?? ?? ?? ?? ?? ?? 84 DB 74 ?? BA ?? ?? ?? ?? EB ?? BA ?? ?? ?? ??',
     fields = {player_count = {'u32', {16}}, panel_entity = {'u32', {9}}, panel_local = {'u32', {92}}, ready_timer = {'u32', {107, 165, 274}}, players = {'rip', {3, 159}, {7, 163}}, player_active = {'u32', {175}}, player_entries = {'u32', {35, 185}}, player_flags = {'u32', {28, 197}}, ui_sound = {'call', {208}, {212}}, timer_idle = {'u32', {169}}, ready_time = {'u32', {278}}, sound_ready_last = {'u32', {287}}, sound_ready = {'u32', {294}}}},
    {name = 'equip_tail', rva = 0x146e5f6, text = '48 8D 8F ?? ?? ?? ?? 48 C7 C2 FF FF FF FF E8 ?? ?? ?? ?? 83 BF ?? ?? ?? ?? 01 74 ?? 48 8B 2D ?? ?? ?? ?? 4C 8D 9F ?? ?? ?? ?? 41 0F B6 43 FC C0 E8 02 A8 01 75 ?? 41 8B 1B 8D 43 FF 3D 94 00 00 00 0F 87 ?? ?? ?? ?? 8B D3 48 8B CD E8 ?? ?? ?? ?? 48 85 C0 75 ?? 49 8B 04 DE 8B 40 04 85 C0 74 ?? FF C6 49 81 C3 ?? ?? ?? ?? 83 FE 04 72 ?? BA 11 34 75 97 E8 ?? ?? ?? ?? 48 8B CF E8 ?? ?? ?? ?? 8B 87 ?? ?? ?? ?? 48 8D 8F ?? ?? ?? ?? 48 69 D0 ?? ?? ?? ?? 48 83 C2 ?? 48 03 D7 E8 ?? ?? ?? ?? 48 8D 8F ?? ?? ?? ?? E8 ?? ?? ?? ?? 8B 87 ?? ?? ?? ?? 48 69 C8 ?? ?? ?? ?? 48 83 C1 ?? 48 03 CF E8 ?? ?? ?? ?? E9 ?? ?? ?? ?? 83 FE FF 74 ?? 48 8D 8F ?? ?? ?? ?? 8B D6 E8 ?? ?? ?? ?? 89 B7 ?? ?? ?? ??',
     fields = {panels = {'u32', {3}}, slots_changed = {'call', {15}, {19}}, refresh = {'call', {157}, {161}}, list_grid = {'u32', {164}}, grid_refresh = {'call', {169}, {173}}, block_stride = {'u32', {145, 182}}, block_base = {'u8', {152, 189}}, save = {'call', {194}, {198}}, grid_mode = {'u32', {21}}, slot_types = {'u32', {38}}, slot_stride = {'u32', {102}}, ui_sound = {'call', {117}, {121}}, close_list = {'call', {125}, {129}}, local_index = {'u32', {131, 175}}, list = {'u32', {138}}, grid = {'u32', {211}}, focus_call = {'call', {218}, {222}}, edit_slot = {'u32', {224}}}},
    {name = 'open_list', rva = 0x146e9d0, text = '40 57 48 81 EC A0 00 00 00 48 8B 05 ?? ?? ?? ?? 48 33 C4 48 89 44 24 70 80 B9 08 28 00 00 00 48 8B F9 0F 85 ?? ?? ?? ?? F7 81 D8 F2 0C 00 00 00 00 08 74 ?? 8B 81 88 F3 0C 00 48 C1 E8 0B A9 FF 07 00 00 0F 85 ?? ?? ?? ?? 0F B6 81 91 39 27 00 48 89 9C 24 B0 00 00 00 48 8D 99 ?? ?? ?? ?? 48 89 AC 24 B8 00 00 00 BD 04 00 00 00 48 89 B4 24 C0 00 00 00 8B F5 0F 29 BC 24 90 00 00 00 44 0F 29 84 24 80 00 00 00 C6 81 ?? ?? ?? ?? 01 88 81 92 39 27 00',
     fields = {panels = {'u32', {91}}, list_open = {'u32', {137}}}},
    {name = 'set_slot', rva = 0x189d050, text = '83 FA 04 0F 83 ?? ?? ?? ?? 48 89 5C 24 08 48 89 74 24 10 57 48 83 EC 20 41 8B D8 8B F2 48 8D B9 78 5B 00 00 8B CB E8 ?? ?? ?? ?? 48 69 CE ?? ?? ?? ?? 8B D0 48 81 C1 ?? ?? ?? ?? 48 03 CF E8 ?? ?? ?? ?? 80 BF 78 D9 00 00 00',
     fields = {slot_stride = {'u32', {46}}, widget_base = {'u32', {55}}, set_widget = {'call', {63}, {67}}}},
}

-- ---------------------------------------------------------------- code search
-- Finds the game's loadout code by byte signatures: each is tried at the known build's
-- address first (instant), else game.dll's executable sections are searched 2 MB per frame.
-- A signature must match exactly once, repeated values must agree, or the feature stays off.
local function parse_sig(sig)
    local bytes = {}
    for part in sig.text:gmatch('%S+') do bytes[#bytes + 1] = part ~= '??' and tonumber(part, 16) or false end
    local best_at, best_len, at, len = 1, 0, nil, 0
    for i = 1, #bytes + 1 do
        if bytes[i] then
            if not at then at, len = i, 0 end
            len = len + 1
            if len > best_len then best_at, best_len = at, len end
        else at = nil end
    end
    local anchor = {}
    for i = best_at, best_at + best_len - 1 do anchor[#anchor + 1] = string.char(bytes[i]) end
    sig.bytes, sig.anchor, sig.anchor_at = bytes, table.concat(anchor), best_at - 1
end

local function sig_matches(blob, pos, sig)           -- pos: 1-based start in blob
    local bytes = sig.bytes
    if pos < 1 or pos + #bytes - 1 > #blob then return false end
    for i = 1, #bytes do
        local b = bytes[i]
        if b and blob:byte(pos + i - 1) ~= b then return false end
    end
    return true
end

local function le32(blob, at)                        -- 0-based
    local a, b, c, d = blob:byte(at + 1, at + 4)
    return a + 256 * b + 65536 * c + 16777216 * d
end
local function s32(blob, at)
    local v = le32(blob, at)
    return v >= 2147483648 and v - 4294967296 or v
end

-- reads the fields of one matched signature (blob = its bytes, rva = where it is)
local function sig_fields(sig, blob, rva)
    local out = {}
    for name, f in pairs(sig.fields or {}) do
        local kind, offsets, nexts = f[1], f[2], f[3]
        local value
        for k, off in ipairs(offsets) do
            local v
            if kind == 'u8' then v = blob:byte(off + 1)
            elseif kind == 'u32' then v = le32(blob, off)
            else v = rva + nexts[k] + s32(blob, off) end        -- 'rip' / 'call': the target's rva
            if value ~= nil and value ~= v then return nil, '"' .. name .. '" differs inside ' .. sig.name end
            value = v
        end
        out[name] = value
    end
    return out
end

local Scan = {}
Scan.__index = Scan

function Scan.new(sigs, read, base, sections)
    local self = setmetatable({ sigs = sigs, read = read, base = base, found = {}, missing = {}, values = {},
                                problems = {}, moved = {}, sections = sections, queue = nil }, Scan)
    for _, sig in ipairs(sigs) do parse_sig(sig) end
    return self
end

function Scan:accept(sig, rva)
    local blob = self.read(self.base + rva, #sig.bytes)
    if not blob then return false end
    local fields, why = sig_fields(sig, blob, rva)
    if not fields then self.problems[#self.problems + 1] = why; return false end
    self.found[sig.name] = rva
    for name, v in pairs(fields) do
        if self.values[name] ~= nil and self.values[name] ~= v then
            self.problems[#self.problems + 1] = '"' .. name .. '" differs between signatures'
        end
        self.values[name] = v
    end
    return true
end

-- true: all found at the known addresses. false: search needed (self.queue is set).
function Scan:start()
    local lost = {}
    for _, sig in ipairs(self.sigs) do
        local blob = self.read(self.base + sig.rva, #sig.bytes)
        if blob and sig_matches(blob, 1, sig) and self:accept(sig, sig.rva) then
            -- found where this build had it
        else lost[#lost + 1] = sig end
    end
    if #lost == 0 then self.done = true; return true end
    self.lost = lost
    self.queue = {}
    for _, s in ipairs(self.sections) do
        local at = s.rva
        while at < s.rva + s.size do
            self.queue[#self.queue + 1] = { at, math.min(2097152 + 256, s.rva + s.size - at) }
            at = at + 2097152
        end
    end
    self.hits = {}
    return false
end

-- one chunk of the search; true when finished
function Scan:step()
    local job = table.remove(self.queue, 1)
    if job then
        local blob = self.read(self.base + job[1], job[2])
        if blob then
            for _, sig in ipairs(self.lost) do
                local from = 1
                while true do
                    local a = blob:find(sig.anchor, from, true)
                    if not a then break end
                    local start = a - sig.anchor_at
                    if sig_matches(blob, start, sig) then
                        local rva = job[1] + start - 1
                        local h = self.hits[sig.name] or {}
                        local dup = false
                        for _, r in ipairs(h) do if r == rva then dup = true end end
                        if not dup then h[#h + 1] = rva end
                        self.hits[sig.name] = h
                    end
                    from = a + 1
                end
            end
        end
    end
    if #self.queue > 0 then return false end
    for _, sig in ipairs(self.lost) do
        local h = self.hits[sig.name] or {}
        if #h == 1 and self:accept(sig, h[1]) then
            self.moved[#self.moved + 1] = sig.name
        elseif #h == 0 then self.missing[sig.name] = 'not found'
        else self.missing[sig.name] = 'found ' .. #h .. ' times' end
    end
    self.done = true
    return true
end

-- ---------------------------------------------------------------- the module
local S = { state = 'idle', why = nil, frames = 0, sigs = SIGS }
local LOADOUT_SCREEN = 11                  -- the Hellpod loadout screen's type on the screen stack
local SLOTS = 4
local INFO_NAME, INFO_ID = 0x10, 4         -- stratagem info: debug name (char *), item id
local OFFER_STRIDE, OFFER_ID, OFFER_ITEM = 0x18, 4, 8
local NEEDED = { 'screen', 'refresh_a', 'refresh_b', 'offers_count', 'kind_frv', 'equip_tail', 'set_slot',
                 'open_list', 'ready_toggle' }
local L, scan, natives, names_cache = {}, nil, {}, nil
local note = function() end

local function u32_at(blob, at) return blob and #blob >= (at or 0) + 4 and le32(blob, at or 0) or nil end
local function rd(address, size) return api.read(address, size) end
local function pointer_at(address)
    local b = rd(address, 8)
    if not b then return nil end
    local lo, hi = le32(b, 0), le32(b, 4)
    local v = lo + hi * 4294967296
    if v < 0x10000 or v >= 0x800000000000 then return nil end
    return v
end
local function global_at(rva) return pointer_at(S.base + rva) end

function S.set_logger(fn) note = fn end

-- game.dll's executable sections: { rva, size }
local function exec_sections(base)
    local dos = rd(base, 64)
    local pe = dos and le32(dos, 60)
    local head = pe and pe < 0x1000 and rd(base + pe, 24)
    if not head or head:sub(1, 4) ~= 'PE\0\0' then return nil end
    local count = head:byte(7) + 256 * head:byte(8)
    local optional = head:byte(21) + 256 * head:byte(22)
    local table_at = base + pe + 24 + optional
    local blob = rd(table_at, count * 40)
    if not blob then return nil end
    local out = {}
    for i = 0, count - 1 do
        local o = i * 40
        local size, rva, flags = le32(blob, o + 8), le32(blob, o + 12), le32(blob, o + 36)
        if flags >= 0x20000000 and math.floor(flags / 0x20000000) % 2 == 1 and size > 0 then
            out[#out + 1] = { rva = rva, size = size }
        end
    end
    return out
end

local function missing_code()
    for _, name in ipairs(NEEDED) do
        if not scan.found[name] then return 'code "' .. name .. '" ' .. (scan.missing[name] or 'not found') end
    end
    if #scan.problems > 0 then return scan.problems[1] end
end

local function make_natives()
    local function cast(proto, rva)
        if api.native then return api.native(proto, rva) end
        if not ffi then return nil end
        local ok, fn = pcall(ffi.cast, proto, S.base + rva)
        return ok and fn or nil
    end
    natives.set_widget = cast('void (*)(uint64_t, uint32_t)', L.set_widget)
    natives.slots_changed = cast('void (*)(uint64_t, int64_t)', L.slots_changed)
    natives.save = cast('void (*)(uint64_t)', L.save)
    natives.close = cast('void (*)(uint64_t)', L.close_list)
    for _, k in ipairs({ 'set_widget', 'slots_changed', 'save', 'close' }) do
        if not natives[k] then return 'native function ' .. k .. ' unavailable' end
    end
end

local function finish_scan()
    local why = missing_code()
    if not why then
        for k, v in pairs(scan.values) do L[k] = v end
        if L.slot_stride < 0x100 or L.slot_stride > 0x10000 then why = 'slot layout' end
        if not why and (L.types < 2 or L.types > 0x1000) then why = 'stratagem table size' end
        L.widget0 = L.grid + L.widget_base                 -- the first slot widget, from the screen
        L.widget_type = L.slot_types - L.widget0           -- a widget's type field
        if not why and (L.widget_type < 4 or L.widget_type >= L.slot_stride) then why = 'slot widget layout' end
    end
    if not why then why = make_natives() end
    if why then S.state, S.why = 'off', why; note('stratagems: not available: ' .. why); return end
    S.state = 'ready'
    note('stratagems: game code found ' .. (#scan.moved == 0 and "at this game version's addresses"
         or ('by search (' .. #scan.moved .. ' moved)')))
end

-- ask for the feature (the Stratagems tab opened); idempotent
function S.request()
    if S.state ~= 'idle' then return end
    S.state = 'starting'
    if not api or not api.module_base then S.state, S.why = 'off', 'no memory access'; return end
    S.base = api.module_base('game.dll')
    if not S.base then S.state, S.why = 'off', 'game.dll not found'; return end
    S.sections = exec_sections(S.base)
    if not S.sections then S.state, S.why = 'off', 'game.dll header unreadable'; return end
    scan = Scan.new(S.sigs, rd, S.base, S.sections)
    if scan:start() then return finish_scan() end
    S.state = 'searching'
    note('stratagems: searching game.dll for moved code')
end

-- per frame while the tab is shown
function S.tick()
    S.frames = S.frames + 1
    if S.state == 'searching' then
        local ok, done = pcall(scan.step, scan)
        if not ok then S.state, S.why = 'off', tostring(done); return end
        if done then finish_scan() end
    end
end

function S.ready() return S.state == 'ready' end
function S.searching() return S.state == 'searching' or S.state == 'starting' end

-- the loadout screen object, or nil
local function loadout_screen()
    local stack = global_at(L.stack)
    if not stack then return nil end
    local head = rd(stack, L.slot + 8)
    if not head or le32(head, 0) ~= LOADOUT_SCREEN then return nil end
    local lo, hi = le32(head, L.slot), le32(head, L.slot + 4)
    local v = lo + hi * 4294967296
    if v < 0x10000 or v >= 0x800000000000 then return nil end
    return v
end

-- a stratagem's info record and debug name, by type
local function info_of(t)
    local info = t > 0 and t < L.types and global_at(L.strat_table + t * 8)
    if info and u32_at(rd(info, 4)) == t then return info end
end

local function debug_name(info)
    local p = pointer_at(info + INFO_NAME)
    local raw = p and rd(p, 48)
    if not raw then return nil end
    local text = raw:match('^([%w_ %-%.]+)%z')
    return text and #text >= 2 and text or nil
end

-- name -> type, type -> name (read once)
local function names()
    if names_cache then return names_cache end
    local by_type, by_name = {}, {}
    for t = 1, L.types - 1 do
        local info = info_of(t)
        local nm = info and debug_name(info)
        if nm then by_type[t], by_name[nm:lower()] = nm, t end
    end
    names_cache = { by_type = by_type, by_name = by_name }
    return names_cache
end

function S.pretty(nm)
    nm = tostring(nm):gsub('^[Ss]tratagem[_ ]', ''):gsub('_', ' ')
    return nm
end

-- item id (info +4) -> true for the stratagems the loadout list offers (owned / available)
local function offered()
    local set = {}
    local offers = global_at(L.offers)
    local first = offers and u32_at(rd(offers + L.first, 4))
    local last = offers and u32_at(rd(offers + L.last, 4))
    local count = offers and u32_at(rd(offers + L.offers_count, 4))
    if not first or not last or not count or last <= first or last - first > 512 or count > 0x10000 then return set end
    local indices = rd(offers + L.indices + first * 4, (last - first) * 4)
    for k = 0, last - first - 1 do
        local index = u32_at(indices, k * 4)
        local entry = index and index < count and rd(offers + L.entries + index * OFFER_STRIDE, OFFER_STRIDE)
        if entry then set[u32_at(entry, OFFER_ITEM)] = true end
    end
    return set
end

-- The current slots: { debug name or false, ... } (4), or nil and why.
function S.read_loadout()
    if not S.ready() then return nil, S.why or 'not ready' end
    local screen = loadout_screen()
    if not screen then return nil, 'Open the Hellpod loadout screen (before a mission) to read or apply.' end
    local head = rd(screen + L.local_index, 4)
    local index = head and le32(head, 0)
    if not index or index > 3 then return nil, 'The loadout screen is still loading.' end
    local out = {}
    for k = 0, SLOTS - 1 do
        local t = u32_at(rd(screen + L.widget0 + k * L.slot_stride + L.widget_type, 4))
        if t == nil then return nil, 'Could not read the slots.' end
        local info = t ~= 0 and info_of(t)
        out[k + 1] = info and debug_name(info) or false
        if t ~= 0 and not out[k + 1] then return nil, 'A slot holds a stratagem this mod cannot name (type ' .. t .. ').' end
    end
    return out
end

-- Applies { name or false, ... } to the four slots, the way the game's own pick does, then saves.
-- Returns true, or false and why. Only stratagems the loadout list offers are put in.
function S.apply(want)
    if not S.ready() then return false, S.why or 'not ready' end
    local screen = loadout_screen()
    if not screen then return false, 'Open the Hellpod loadout screen (before a mission) first.' end
    local head = rd(screen + L.local_index, 4)
    local index = head and le32(head, 0)
    if not index or index > 3 then return false, 'The loadout screen is still loading.' end
    local timer = u32_at(rd(screen + L.panels + L.ready_timer, 4))
    if timer ~= L.timer_idle then return false, 'Not while you are ready: un-ready first.' end
    local list_open = rd(screen + L.list_open, 1)
    local dict = names()
    local offers = offered()
    local types, skipped = {}, {}
    for k = 1, SLOTS do
        local nm = want[k]
        if nm then
            local t = dict.by_name[nm:lower()]
            local info = t and info_of(t)
            local item = info and u32_at(rd(info + INFO_ID, 4))
            if not t then skipped[#skipped + 1] = S.pretty(nm) .. ' (unknown in this game version)'
            elseif not (item and offers[item]) then skipped[#skipped + 1] = S.pretty(nm) .. ' (not available to you)'
            else types[k] = t end
        end
        types[k] = types[k] or 0
    end
    if list_open and list_open:byte(1) ~= 0 then natives.close(screen) end
    for k = 0, SLOTS - 1 do
        local widget = screen + L.widget0 + k * L.slot_stride
        local now = u32_at(rd(widget + L.widget_type, 4))
        if now ~= types[k + 1] then natives.set_widget(widget, types[k + 1]) end
    end
    natives.slots_changed(screen + L.panels, -1)
    natives.save(screen + L.block_base + index * L.block_stride)
    note('stratagems: applied ' .. table.concat((function()
        local t = {}
        for k = 1, SLOTS do t[k] = tostring(types[k]) end
        return t
    end)(), ','))
    return true, nil, skipped
end

function S.report()
    local lines = { 'Stratagem presets: ' .. (S.state == 'ready' and 'on' or ('NOT AVAILABLE (' .. tostring(S.why or S.state) .. ')')) }
    if scan and #scan.moved > 0 then lines[#lines + 1] = 'Game code found by search: ' .. table.concat(scan.moved, ', ') end
    return lines
end

return S
end)()
