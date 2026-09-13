-- Reads progression only; never grants achievements or alters the game save.
local mod = RegisterMod("TBOI Progress Exporter", 1)
local ready, lastJSON, frames = false, nil, 0
local keys = {"MomsHeart","Isaac","Satan","BossRush","BlueBaby","Lamb","MegaSatan","UltraGreed","Hush","UltraGreedier","Delirium","Mother","Beast"}
local function arr(t)
    local s = {}
    for _,v in ipairs(t) do s[#s+1] = tostring(v) end
    return "[" .. table.concat(s, ",") .. "]"
end
local function exportNow()
    if not ready or not Isaac.GetPersistentGameData then return end
    local pgd = Isaac.GetPersistentGameData()
    if not pgd then return end
    local achievements, items, challenges, chars = {}, {}, {}, {}
    for id=1,1000 do
        local ok,v = pcall(function() return pgd:Unlocked(id) end)
        if ok and v then achievements[#achievements+1] = id end
    end
    for id=1,1200 do
        local ok,v = pcall(function() return pgd:IsItemInCollection(id) end)
        if ok and v then items[#items+1] = id end
    end
    for id=1,100 do
        local ok,v = pcall(function() return pgd:IsChallengeCompleted(id) end)
        if ok and v then challenges[#challenges+1] = id end
    end
    for id=0,40 do
        local ok,m = pcall(function() return Isaac.GetCompletionMarks(id) end)
        if ok and type(m)=="table" then
            local fields = {}
            for _,k in ipairs(keys) do fields[#fields+1] = '"'..k..'":'..tostring(m[k] or 0) end
            chars[#chars+1] = '"'..id..'":{'..table.concat(fields,",")..'}'
        end
    end
    local json = '{"format":"tboi-progress-export-v2","source":"game","exporterVersion":3,'
      .. '"achievements":'..arr(achievements)..',"collectedItems":'..arr(items)
      .. ',"completedChallenges":'..arr(challenges)..',"completionMarks":{'..table.concat(chars,",")..'}}'
    if json ~= lastJSON then
        mod:SaveData(json)
        lastJSON = json
        Isaac.DebugString("[TBOI Progress Exporter] Progress updated (v3).")
    end
end
local function safeExport()
    local ok,err = pcall(exportNow)
    if not ok then Isaac.DebugString("[TBOI Progress Exporter] Export error: "..tostring(err)) end
end
mod:AddCallback(ModCallbacks.MC_POST_GAME_STARTED, function()
    ready = true
    lastJSON = nil
    safeExport()
end)
mod:AddCallback(ModCallbacks.MC_POST_UPDATE, function()
    frames = frames + 1
    if frames % 120 == 0 then safeExport() end
end)
mod:AddCallback(ModCallbacks.MC_PRE_GAME_EXIT, function()
    safeExport()
    ready = false
end)
mod:AddCallback(ModCallbacks.MC_POST_GAME_END, safeExport)
if ModCallbacks.MC_POST_SAVESLOT_LOAD then
    mod:AddCallback(ModCallbacks.MC_POST_SAVESLOT_LOAD, function(_, slot, selected, raw)
        ready = selected and raw ~= 0
        lastJSON = nil
        if ready then safeExport() end
    end)
end
for _,name in ipairs({"MC_POST_ACHIEVEMENT_UNLOCK", "MC_POST_COMPLETION_MARK_GET"}) do
    if ModCallbacks[name] then mod:AddCallback(ModCallbacks[name], safeExport) end
end
