import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

class HelperTest(unittest.TestCase):
    def test_validation_and_atomic_state(self):
        with tempfile.TemporaryDirectory() as directory:
            previous=os.environ.get('APPDATA')
            os.environ['APPDATA']=directory
            try:
                spec=importlib.util.spec_from_file_location('helper','helper/tboi_sync_helper.py')
                helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
                data={'achievements':[1,2],'collectedItems':[],'completedChallenges':[],'completionMarks':{}}
                self.assertEqual(helper.validate_progress(data),data)
                with self.assertRaises(ValueError): helper.validate_progress({'achievements':[]})
                with self.assertRaises(ValueError): helper.validate_progress({**data,'achievements':[True]})
                path=Path(directory)/'state.json'
                helper.write_json(path,data)
                self.assertEqual(helper.read_json(path),data)
                self.assertFalse(path.with_suffix('.json.tmp').exists())
            finally:
                if previous is None: os.environ.pop('APPDATA',None)
                else: os.environ['APPDATA']=previous

if __name__=='__main__': unittest.main()
