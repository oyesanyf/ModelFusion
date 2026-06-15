import unittest
import os
import pandas as pd
import tempfile
import asyncio
from core.data_analyst import handle_data_analyst


class TestDataAnalystReport(unittest.TestCase):
    def test_report_written(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'data.csv')
            pd.DataFrame({'a':[1,2,3], 'b':[2,3,4]}).to_csv(path, index=False)
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(handle_data_analyst(path, 'test'))
            loop.close()
            self.assertTrue(result['success'])
            self.assertIn('Report saved:', result['content'])


if __name__ == '__main__':
    unittest.main()


