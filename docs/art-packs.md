# A branch with new pictures, onto the packs

Since P814 each game's pictures are one pack, `games/packs/<set>.pak`, and `games/art/*.bin` is gone. A branch that
was started before, and adds or changes `.bin` files, moves onto the packs in four steps.

1. Merge or rebase with renames off, and with folder renames off:
   `git -c merge.directoryRenames=false merge -X no-renames origin/master`. For a rebase, put `rebase` in place of
   `merge`. With renames on, git takes a removed `.bin` and a new pack for a rename, for example
   `games/art/bucket_scene.bin` to `games/packs/bucket.pak`. Then it takes `games/art` as moved to `games/packs`, and
   it moves the branch's new `.bin` files there. `-X no-renames` alone does not stop this folder move (BUBBLE's merge,
   2026-11-14). Resolve a conflict in `games/art_index.py` with master's copy: step 3 writes it again.
2. Remove the `.bin` files the branch still has: `git rm games/art/*.bin`.
3. Paint again from the repository root: `python3 art/paint.py`. It writes the packs and `games/art_index.py`.
4. Move the set's tests to `export.pack_bytes(name)`: a picture's bytes as committed, read from its pack through
   `games/art_index.py`. A test never opens a picture file itself.

`.gitattributes` marks `*.pak` as binary, so git never tries to merge or diff a pack as text.
