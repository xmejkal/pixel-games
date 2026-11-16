"""The twin rule (P850, stage 0b-2 of the engine plan): every part that main.py chooses has two versions, and a test
runs both on the same input. TWINS names that test for each part name of a choose call in games/main.py, read with
ast, so a part without a row fails here. Run from the repository root: python3 -B -m unittest tests.test_twins.
--- MVP (P850) ---"""

import ast
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(os.path.dirname(HERE), "games", "main.py")
# part -> the test that runs its reference and its fast version on the same blocks
TWINS = {
    "sum": "tests.test_voices.TestVoices.test_the_viper_sum_gives_the_plain_samples_on_each_named_block",
    "volume": "tests.test_volume.ViperMasterVolumeTest.test_the_viper_scale_gives_the_naive_samples_on_each_named_block",
}


def chosen_parts(source):
    """The part name of each choose(...) call in source, in their order."""
    return [node.args[0].value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", None)) == "choose"
            and node.args and isinstance(node.args[0], ast.Constant)]


def without_twin(source, twins=TWINS):
    """The parts of source's choose calls that have no row in twins."""
    return [part for part in chosen_parts(source) if part not in twins]


class TwinTest(unittest.TestCase):
    def test_every_chosen_part_has_a_twin_test(self):
        with open(MAIN) as f:
            source = f.read()
        self.assertEqual(["sum", "volume"], chosen_parts(source))
        self.assertEqual([], without_twin(source))

    def test_a_part_without_a_row_fails(self):
        source = 'chooser.choose("sum", a, b, "viper")\nchooser.choose("bodies", c, d, "c")\n'
        self.assertEqual(["bodies"], without_twin(source))

    def test_each_row_names_a_part_and_a_test_that_exists(self):
        with open(MAIN) as f:
            self.assertEqual(sorted(chosen_parts(f.read())), sorted(TWINS))
        for part, name in TWINS.items():
            with self.subTest(part):
                self.assertTrue(defines(name), name)


def defines(name):
    """True when tests/<module>.py defines the class and its test method that name (tests.<module>.<class>.<test>)
    names, read with ast, so this test imports no other test module."""
    _, module, cls, method = name.split(".")
    with open(os.path.join(HERE, module + ".py")) as f:
        tree = ast.parse(f.read())
    return any(isinstance(node, ast.ClassDef) and node.name == cls and
               any(isinstance(item, ast.FunctionDef) and item.name == method for item in node.body)
               for node in tree.body)


if __name__ == "__main__":
    unittest.main()
