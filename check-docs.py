from filecmp import dircmp
from os import path

from mistune import BlockLexer

from config import *

parser = BlockLexer()


def head_count(token, level):
    return len(list(filter(lambda x: x["type"] == "heading" and x["level"] == level, token)))


def cmp_md_struct(file1: str, file2: str) -> None:
    token1, token2 = parser.parse(open(file1, encoding="utf-8").read()), parser.parse(
        open(file2, encoding="utf-8").read())
    for level in range(4):
        if head_count(token1, level) != head_count(token2, level):
            print("diff struct found, level %d in %s and %s" % (level, file1, file2))


def cmp_files(dcmp: dircmp) -> None:
    for file_name in (dcmp.left_only + dcmp.right_only):
        print("diff file %s found in %s and %s" % (file_name, dcmp.left, dcmp.right))
    for file_name in dcmp.common_files:
        cmp_md_struct(path.join(dcmp.left, file_name), path.join(dcmp.right, file_name))
    for sub_dcmp in dcmp.subdirs.values():
        cmp_files(sub_dcmp)


if __name__ == "__main__":
    cmp_files(dircmp(ZH_DOC_PATH, EN_DOC_PATH, ignore=["__init__.py", "images", ".git", "README.md", ".DS_Store"]))
