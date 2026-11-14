"""Each game loads only its own art set (P773): pictures.load on the Mac, from the committed games/packs. A set holds
its own pictures and no other set's, a later load or the box's switch frees the last set, Fire reads only the sky, the
board's path reads every set into the one s3lcd pool made as big as the largest pack, and each game's module names
only pictures of its own set. A set is one pack (P814): read in reads of at most CHUNK_SIZE, refused when its size or
header is another build's, only's pictures read alone, every entry inside its pack. Run from the repository root:
python3 -B -m unittest tests.test_pictures_sets."""

import ast
import contextlib
import hashlib
import io
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "games")
sys.path.insert(0, os.path.join(ROOT, "art"))  # export: the committed pictures
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
from export import pack_bytes  # noqa: E402

# Each game module and the sets its pictures come from (a set and the only names it loads, None for all)
MODULES = {
    "fire.py": (("runner", ("sky",)),),
    "marshmallow.py": (("runner", ("sky",)),),
    "arcade.py": (("flappy", None), ("runner", None)),
    "track.py": (("runner", None),),
    "arcade2.py": (("stack", None),),
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

    def test_on_the_board_every_set_reads_into_the_one_pool_as_big_as_the_largest_pack(self):
        pool = Pool()
        sys.modules["s3lcd"] = pool
        sizes = [total for path, total, build_id in art_index.PACKS.values()]
        packs = os.path.join(GAMES, "packs")
        largest = max(os.path.getsize(os.path.join(packs, name)) for name in os.listdir(packs))
        self.assertEqual(largest, max(sizes))  # the pool fits the largest pack file, its header included
        for game in ("rescue", "meteors", "runner"):
            with self.subTest(game=game):
                self.assertTrue(pictures.load(game))
                name = art_index.PICTURE_SETS[game][0]
                view = pictures.PICS[name][2]
                self.assertIs(pool.buf, view.obj)  # a slice of the pool, not a copy in the heap
                self.assertEqual(pack_bytes(name), bytes(view))
        self.assertEqual({largest}, set(pool.sizes))
        self.assertLess(largest, sum(sizes) // 2)

    def test_no_game_reads_every_pack(self):
        self.assertTrue(pictures.load())
        self.assertEqual(set(art_index.ART), set(pictures.PICS))
        self.assertEqual(set(art_index.LAYER_SETS), set(pictures.SETS))
        for name in art_index.ART:
            with self.subTest(name=name):
                self.assertEqual(pack_bytes(name), bytes(pictures.PICS[name][2]))
        for game, layers in pictures.SETS.items():
            for name, *_, view in layers:
                self.assertEqual(pack_bytes(name), bytes(view))


class Recorded:
    """A pack file that records each read's size and the bytes it gave."""

    def __init__(self, f, log):
        self.f, self.log = f, log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.f.close()

    def seek(self, *args):
        return self.f.seek(*args)

    def readinto(self, view):
        n = self.f.readinto(view)
        self.log.append((len(view), n))
        return n


class PacksTest(unittest.TestCase):
    """The packs (P814): one file per set, read in chunks, checked, and only what is asked for."""

    def setUp(self):
        self.root, self.reads = pictures.ROOT, []
        pictures.ROOT = os.path.join(GAMES, "")
        pictures.free()
        pictures.open = lambda path, mode: Recorded(open(path, mode), self.reads)  # pictures' own open, recorded
        self.addCleanup(self.restore)

    def restore(self):
        del pictures.open
        pictures.free()
        pictures.ROOT = self.root

    def test_a_read_never_asks_for_more_than_a_chunk(self):
        self.assertLessEqual(pictures.CHUNK_SIZE, 8192)  # about 6 ms a read on the board, under the 48 ms late limit
        self.assertTrue(pictures.load("runner"))
        self.assertLessEqual(max(asked for asked, _ in self.reads), pictures.CHUNK_SIZE)
        self.assertEqual(art_index.PACKS["runner"][1], sum(got for _, got in self.reads))  # the whole pack, once
        self.assertGreater(len(self.reads), art_index.PACKS["runner"][1] // pictures.CHUNK_SIZE)

    def test_only_reads_the_header_and_its_pictures(self):
        self.assertTrue(pictures.load("runner", ("sky",)))
        self.assertEqual(pictures.HEADER + 320 * 240 * 2, sum(got for _, got in self.reads))
        self.assertEqual(pack_bytes("sky"), bytes(pictures.PICS["sky"][2]))

    def stale(self, change):
        """load("bucket") from a copy of the packs whose bucket pack change(data) altered: what it says."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        shutil.copytree(os.path.join(GAMES, "packs"), os.path.join(tmp.name, "packs"))
        path = os.path.join(tmp.name, "packs", "bucket.pak")
        with open(path, "rb") as f:
            data = f.read()
        with open(path, "wb") as f:
            f.write(change(data))
        pictures.ROOT = os.path.join(tmp.name, "")
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertFalse(pictures.load("bucket"))
        self.assertEqual({}, pictures.PICS)
        return said.getvalue()

    def test_a_stale_pack_is_refused_aloud(self):
        other = lambda data: data[:8] + bytes(b ^ 0xFF for b in data[8:16]) + data[16:]  # noqa: E731  another build
        longer = lambda data: data + bytes(2)  # noqa: E731
        shorter = lambda data: data[:-2]  # noqa: E731
        magic = lambda data: b"OLDPACK1" + data[8:]  # noqa: E731
        for change in (other, longer, shorter, magic):
            with self.subTest(change=change):
                self.assertIn("stale art: copy games/packs", self.stale(change))

    def test_a_missing_pack_is_refused_aloud(self):
        pictures.ROOT = os.path.join(GAMES, "nowhere", "")
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertFalse(pictures.load("rescue"))
        self.assertIn("stale art: copy games/packs", said.getvalue())


class PackFilesTest(unittest.TestCase):
    """The committed packs against the index: each one's header and size, and every entry inside its pack."""

    def test_each_pack_s_header_is_its_build(self):
        for game, (path, total, build_id) in art_index.PACKS.items():
            with self.subTest(game=game), open(os.path.join(GAMES, path), "rb") as f:
                data = f.read()
                self.assertEqual(total, len(data))
                self.assertEqual(pictures.MAGIC, data[:8])
                self.assertEqual(build_id, data[8:16].hex())
                self.assertEqual(build_id, hashlib.sha256(data[pictures.HEADER:]).hexdigest()[:16])

    def test_every_entry_lies_inside_its_pack(self):
        for name, (w, h, game, at) in art_index.ART.items():
            with self.subTest(name=name):
                self.assertIn(name, art_index.PICTURE_SETS[game])  # a switch opens its own set's pack only
                self.assertLessEqual(pictures.HEADER, at)
                self.assertLessEqual(at + w * h * 2, art_index.PACKS[game][1])
                self.assertEqual(0, at % 2)
        for game, rows in art_index.LAYER_SETS.items():
            for name, top, w, h, speed, keyed, layer_set, at in rows:
                self.assertEqual(art_index.ART[name], (w, h, layer_set, at))


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
