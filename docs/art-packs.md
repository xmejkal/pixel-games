# A branch with new pictures, onto the packs

Since P814 each game's pictures are one pack, `games/packs/<set>.pak`, and `games/art/*.bin` is gone. A branch that
was started before, and adds or changes `.bin` files, moves onto the packs in four steps.

1. Rebase or merge with renames off: `git rebase -X no-renames origin/master` (or `git merge -X no-renames
   origin/master`). With renames on, git takes a removed `.bin` and a new pack for a rename, for example
   `games/art/bucket_scene.bin` to `games/packs/bucket.pak`, and moves the branch's new `.bin` files into
   `games/packs`.
2. Remove the `.bin` files the branch still has: `git rm games/art/*.bin`.
3. Paint again from the repository root: `python3 art/paint.py`. It writes the packs and `games/art_index.py`.
4. Move the set's tests to `export.pack_bytes(name)`: a picture's bytes as committed, read from its pack through
   `games/art_index.py`. A test never opens a picture file itself.

`.gitattributes` marks `*.pak` as binary, so git never tries to merge or diff a pack as text.
