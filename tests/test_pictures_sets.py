"""Each game loads only its own art set (P773): pictures.load on the Mac, from the committed games/art. A set holds its
own pictures and no other set's, a later load or the box's switch frees the last set, Fire reads only the sky, the
board's path reads every set into the one s3lcd pool made as big as the largest set, and each game's module names
only pictures of its own set. Run from the repository root: python3 -B -m unittest tests.test_pictures_sets."""

import ast
import contextlib
import io
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "games")
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, GAMES)
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
    time.ticks_us = lambda: int(time.perf_counter() * 1e6)
    time.ticks_ms = lambda: int(time.perf_counter() * 1e3)
if not hasattr(time, "ticks_add"):
    time.ticks_add = lambda a, b: a + b

import app  # noqa: E402
import art_index  # noqa: E402
import gfx  # noqa: E402
import pictures  # noqa: E402

# Each game module and the sets its pictures come from (a set and the only names it loads, None for all)
MODULES = {
    "fire.py": (("runner", ("sky",)),),
    "marshmallow.py": (("runner", ("sky",)),),
    "arcade.py": (("flappy", None), ("runner", None), ("snake", None)),
    "track.py": (("runner", None),),
    "arcade2.py": (("stack", None), ("gravpong", None)),
    "bucket.py": (("bucket", None),),
    "meteors.py": (("meteors", None),),
    "rescue.py": (("rescue", None),),
}


class Pool:
    """s3lcd's pool as the driver makes it: the first call's size is kept, a bigger one later raises."""

    def __init__(self):
        self.sizes, self.buf = [], None

    def pool(self, size):
        self.sizes.append(size)
        if self.buf is None:
            self.buf = bytearray(size)
        elif size > len(self.buf):
            raise ValueError("the pool is smaller: reset the board")
        return self.buf


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.root = pictures.ROOT
        pictures.ROOT = os.path.join(GAMES, "")
        pictures.free()
        self.addCleanup(self.restore)

    def restore(self):
        pictures.free()
        pictures.ROOT = self.root
        sys.modules.pop("s3lcd", None)

    def test_a_game_loads_only_its_own_set(self):
        self.assertTrue(pictures.load("rescue"))
        self.assertEqual(set(art_index.PICTURE_SETS["rescue"]), set(pictures.PICS))
        self.assertNotIn("meteors_sky", pictures.PICS)
        self.assertIn("rescue_smoke0", pictures.PICS)  # an alias of Meteors' smoke comes with the set that names it

    def test_a_later_load_frees_the_last_set(self):
        pictures.load("rescue")
        self.assertTrue(pictures.load("flappy"))
        self.assertFalse([n for n in pictures.PICS if n.startswith("rescue_")])
        self.assertEqual(["flappy"], list(pictures.SETS))

    def test_fire_reads_only_the_sky(self):
        self.assertTrue(pictures.load("runner", ("sky",)))
        self.assertEqual(["sky"], list(pictures.PICS))
        self.assertEqual({}, pictures.SETS)

    def test_the_same_set_again_reads_nothing(self):
        pictures.load("stack")
        view = pictures.PICS["stack_noon"][2]
        self.assertTrue(pictures.load("stack"))
        self.assertIs(view, pictures.PICS["stack_noon"][2])

    def test_the_box_s_switch_frees_the_last_game_s_set(self):
        class Painted:
            name, state = "painted", gfx.PLAY

            def __init__(self):
                pictures.load("bucket")

        class Plain:
            name, state = "plain", gfx.PLAY

        class Out:
            def clear(self):
                pass

            def reset(self):
                pass

        box = app.App(None, lambda: 1, lambda: 1, games=(Painted, Plain), out=Out())
        with contextlib.redirect_stdout(io.StringIO()):  # the box says each game's name
            box.start()
            self.assertIn("bucket_scene", pictures.PICS)
            box.switch()
        self.assertEqual({}, pictures.PICS)

    def test_on_the_board_every_set_reads_into_the_one_pool_as_big_as_the_largest_set(self):
        pool = Pool()
        sys.modules["s3lcd"] = pool
        largest = max(sum(pictures.files_of((game,)).values()) for game in art_index.PICTURE_SETS)
        for game in ("rescue", "meteors", "runner"):
            with self.subTest(game=game):
                self.assertTrue(pictures.load(game))
                name = art_index.PICTURE_SETS[game][0]
                w, h, path = art_index.ART[name]
                view = pictures.PICS[name][2]
                self.assertIs(pool.buf, view.obj)  # a slice of the pool, not a copy in the heap
                with open(os.path.join(GAMES, path), "rb") as f:
                    self.assertEqual(f.read(), bytes(view))
        self.assertEqual({largest}, set(pool.sizes))
        self.assertLess(largest, sum(pictures.files_of(tuple(art_index.PICTURE_SETS)).values()) // 2)


class ModulesTest(unittest.TestCase):
    def test_each_game_module_names_only_pictures_of_its_own_set(self):
        for module, sets in MODULES.items():
            own = {n for game, only in sets for n in art_index.PICTURE_SETS[game] if only is None or n in only}
            with open(os.path.join(GAMES, module)) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    continue
                word = node.value
                stem = word.split("%")[0]
                if word in art_index.ART:
                    with self.subTest(module=module, name=word):
                        self.assertIn(word, own)
                elif "%" in word and len(stem) > 3 and any(n.startswith(stem) for n in art_index.ART):
                    with self.subTest(module=module, pattern=word):
                        self.assertTrue(any(n.startswith(stem) for n in own))

    def test_each_game_loads_the_set_its_module_is_checked_against(self):
        import fire
        import meteors
        self.assertEqual(MODULES["fire.py"][0], fire.Fire.ART)
        self.assertEqual(MODULES["meteors.py"][0], meteors.Meteors.ART)


if __name__ == "__main__":
    unittest.main()
