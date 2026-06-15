import unittest
from core.workflow_dsl import parse_workflow


class TestWorkflowDSL(unittest.TestCase):
    def test_parse(self):
        text = """
        # comment
        semantic task=analyze key=value
        temporal key=1 other=2
        """
        steps = parse_workflow(text)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].task, 'semantic')
        self.assertEqual(steps[0].params['task'], 'analyze')
        self.assertEqual(steps[1].params['key'], '1')


if __name__ == '__main__':
    unittest.main()


