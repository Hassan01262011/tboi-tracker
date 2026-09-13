import json
import unittest
from pathlib import Path
from lupa import LuaRuntime

class ExporterTest(unittest.TestCase):
    def test_continuous_export(self):
        lua = LuaRuntime()
        lua.execute('''
          callbacks={}; saved={}; unlocked={ [1]=true }
          ModCallbacks={MC_POST_GAME_STARTED=1,MC_POST_UPDATE=2,MC_PRE_GAME_EXIT=3,
            MC_POST_GAME_END=4,MC_POST_SAVESLOT_LOAD=5,MC_POST_ACHIEVEMENT_UNLOCK=6,
            MC_POST_COMPLETION_MARK_GET=7}
          function RegisterMod() return {
            AddCallback=function(_,id,fn) callbacks[id]=fn end,
            SaveData=function(_,s) saved[#saved+1]=s end} end
          Isaac={DebugString=function() end,
            GetPersistentGameData=function() return {
              Unlocked=function(_,id) return unlocked[id] end,
              IsItemInCollection=function(_,id) return id==1 end,
              IsChallengeCompleted=function() return false end} end,
            GetCompletionMarks=function() return {Isaac=2} end}
        ''')
        lua.execute(Path('helper/exporter/main.lua').read_text())
        lua.execute('callbacks[2](); callbacks[5](nil,1,false,0)')
        self.assertEqual(len(lua.globals().saved),0)
        lua.execute('callbacks[1]()')
        self.assertEqual(len(lua.globals().saved),1)
        lua.execute('for i=1,120 do callbacks[2]() end')
        self.assertEqual(len(lua.globals().saved),1)
        lua.execute('unlocked[2]=true;callbacks[6]()')
        self.assertEqual(json.loads(lua.globals().saved[2])['achievements'],[1,2])
        lua.execute('unlocked[3]=true;for i=1,120 do callbacks[2]() end')
        self.assertEqual(json.loads(lua.globals().saved[3])['achievements'],[1,2,3])
        lua.execute('unlocked[4]=true;callbacks[3]()')
        self.assertEqual(json.loads(lua.globals().saved[4])['achievements'],[1,2,3,4])
        lua.execute('callbacks[1]()')
        self.assertEqual(len(lua.globals().saved),5)

if __name__=='__main__': unittest.main()
