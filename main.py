import argparse
import os
from typing import Any, Dict, List, Set, Tuple
import sys
import hashlib
import itertools

HASH_BUF_BYTES = 65536
IGNORED_FILES = ['.DS_Store', '.gdoc', '.gsheet', '.gslides']

parser = argparse.ArgumentParser(
        prog = 'no_file_left_behind',
        description = 'Discover files that are missing from an archive.')

parser.add_argument('--archive', type=str, help='Path to the archive being validated. You expect (or want) this directory to contain a superset of all the files in --scratch.')
parser.add_argument('--scratch', type=str, help='Path to the scratch data being checked against the archive.')

parser.add_argument('--output', type=str, default=None, help='Directory to output reports to.')


class LazyFile:
    def __init__(self, full_path:str):
        self.full_path = full_path
        self._size = None
        self._sha1 = None

    @property
    def size(self):
        if self._size is None:
            self._size = os.path.getsize(self.full_path)
        return self._size

    @property
    def sha1(self):
        if self._sha1 is None:
            sha1 = hashlib.sha1()
            with open(self.full_path, 'rb') as f:
                while True:
                    data = f.read(HASH_BUF_BYTES)
                    if not data:
                        break
                    sha1.update(data)
            self._sha1 = sha1.hexdigest()
        return self._sha1

    def ignored_by_path(self):
        for pattern in IGNORED_FILES:
            if self.full_path.endswith(pattern):
                return True
        return False


def ScratchFile(LazyFile):
    def __init__(self):
        super().__init__()

    

def read_files(directory_or_file: str) -> List[LazyFile]:
    res = []
    total_files = 0

    if os.path.isfile(directory_or_file):
        return [LazyFile(directory_or_file)]
    for (dirpath, dirnames, filenames) in os.walk(directory_or_file):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            lazy = LazyFile(full_path)
            res.append(lazy)
            total_files += 1

    print(f'A total of {total_files} were contained in {directory_or_file}')
    return res


def group_by(files: List[LazyFile], func) -> Dict[Any, List[LazyFile]]:
    res = {}
    # TODO: add loading bars or something.
    for f in files:
        res.setdefault(func(f), []).append(f)
    return res


def match_by(scratch, archive, funcs) -> Tuple[List[LazyFile], List[LazyFile]]:
    if len(funcs) == 0:
        return scratch, []

    scratch_group = group_by(scratch, funcs[0])
    archive_group = group_by(archive, funcs[0])
    matching_keys = set(scratch_group) & set(archive_group)
    non_matching_keys = set(scratch_group) - matching_keys

    no_match = list(itertools.chain.from_iterable([scratch_group[k] for k in non_matching_keys]))
    matching = []
    for k in matching_keys:
        match_on_next_key, no_match_on_next_key = match_by(scratch_group[k], archive_group[k], funcs[1::])
        matching += match_on_next_key
        no_match += no_match_on_next_key
    return matching, no_match


def write_paths_to_file(files: List[LazyFile], out_file: str) -> None:
    files = [f.full_path for f in files]
    files.sort()
    with open(out_file, 'w') as f:
        f.write('\n'.join(files)+'\n')


def main():
    args = parser.parse_args()
    scratch = read_files(args.scratch)
    # TODO: detect archive files that are just links to shared drives.
    archive = read_files(args.archive)

    # Ignore .DS_STORE and other spammy metadata
    scratch = list(filter(lambda f: not f.ignored_by_path(), scratch))

    matched, no_match = match_by(scratch, archive, [lambda f: f.size, lambda f: f.sha1])

    # TODO: Detect creation data differences when matched
    print(f'{len(no_match)}/{len(scratch)} scratch files do not appear in the archive ({len(archive)} files).')

    # duplicates
    # missing
    if args.output is not None:
        write_paths_to_file(matched, os.path.join(args.output, 'duplicates.txt'))
        write_paths_to_file(no_match, os.path.join(args.output, 'missing.txt'))

    # TODO: for files that don't have an exact size match, attempt to
    # find similar files in the archive. For example, files named the same way, or similar pictures.


if __name__ == '__main__':
    main()
