import os
import re

import mistune
from bs4 import BeautifulSoup as bs
from tqdm import tqdm

from config import *

'''
Rule from https://github.com/tensorflow/tensorflow/tree/master/tensorflow/g3doc

* @{tf.symbol} to make a link to the reference page for a Python
    symbol.  Note that class members don't get their own page, but the
    syntax still works, since @{tf.MyClass.method} links to the right
    part of the tf.MyClass page.

* @{tensorflow::symbol} to make a link to the reference page for a C++
    symbol. (This only works for a few symbols but will work for more soon.)

* @{$doc_page} to make a link to another (not an API reference) doc
page. To link to
- red/green/blue/index.md use @{$blue} or @{$green/blue},
- foo/bar/baz.md use @{$baz} or @{$bar/baz}.
The shorter one is preferred, so we can move pages around without
breaking these references. The main exception is that the Python API
guides should probably be referred to using @{$python/<guide-name>}
to avoid ambiguity. To link to an anchor in that doc and use
different link text (by default it uses the title of the target
page) use:
@{$doc_page#anchor-tag$link-text}
(You can skip #anchor-tag if you just want to override the link text).
'''


def find_dir(string, path):
    for _path, _, files in os.walk(path):
        if string + ".md" in files:
            return os.path.join(_path, string)
    raise Exception("couldn't find file: %s" % (string))


def use_origin_url(key):
    dic = {"xla": ("https://www.tensorflow.org/performance/xla/", "XLA 编译器")}
    return dic.get(key)


class CustomRenderer(mistune.Renderer):
    def super_link(self, link, text):
        return '<a href="%s">%s</a>' % (link, text)


class CustomInlineLexer(mistune.InlineLexer):
    def __init__(self, renderer, **kwargs):
        super().__init__(renderer, **kwargs)
        self.file_path = None

    def enable_super_link(self):
        self.rules.super_link = re.compile(r'.*@{(.+?)}.*', re.S)
        self.default_rules.insert(0, 'super_link')

    def output_super_link(self, m):
        sentence = m.group(1)
        if "\n" in sentence:
            sentence = sentence.replace("\n", " ")
        try:
            if "tensorflow::" in sentence:
                return self.renderer.super_link(
                    "https://www.tensorflow.org/api_docs/cc/class/" + re.sub(r"\$.+", "", sentence).lower().replace(
                        "::",
                        "/"),
                    "<code>%s</code>" % re.sub(r"\$.+", "", sentence))
            elif "tf." in sentence or "tfdbg." in sentence:

                return self.renderer.super_link(
                    "https://www.tensorflow.org/api_docs/python/" + re.sub(r"\$.+", "", sentence).replace(".", "/"),
                    "<code>%s</code>" % re.sub(r"\$.+", "", sentence))
            else:
                param = ""
                if len(sentence.split("$")) == 2:
                    url = os.path.join("./", self.file_path, sentence.split("$")[1].replace(self.file_path + "/", ""))
                    if not os.path.exists(os.path.join(ZH_DOC_PATH, url + ".md")):
                        url = sentence.split("$")[1].replace(self.file_path + "/", "")
                    if not os.path.exists(os.path.join(ZH_DOC_PATH, url + ".md")):
                        try:
                            url = find_dir(sentence.split("$")[1].split("/")[-1], ZH_DOC_PATH).replace(ZH_DOC_PATH, "")[
                                  1:]
                        except Exception:
                            url, name = use_origin_url(sentence.split("$")[1])
                            return self.renderer.super_link(url, name)
                    name = list(filter(lambda x: x["type"] == "heading" and x["level"] == 1, mistune.BlockLexer().parse(
                        open(os.path.join(ZH_DOC_PATH, url + ".md"), encoding="utf-8").read())))[0]["text"]
                else:
                    if "#" in sentence:
                        param = re.compile("\#(.+?)\$").findall(sentence)[0]
                        sentence = sentence.replace("#" + param, "")
                    url = os.path.join("./", self.file_path,
                                       sentence.split("$")[1].replace(self.file_path + "/", "").strip().lstrip())
                    if not os.path.exists(os.path.join(ZH_DOC_PATH, url + ".md")):
                        url = sentence.split("$")[1].replace(self.file_path + "/", "")
                    if not os.path.exists(os.path.join(ZH_DOC_PATH, url + ".md")):
                        url = sentence.split("$")[1].replace(self.file_path + "/", "") + "/index"
                    if not os.path.exists(os.path.join(ZH_DOC_PATH, url + ".md")):
                        url = os.path.join(self.file_path,
                                           sentence.split("$")[1].replace(self.file_path + "/",
                                                                          "").strip().lstrip()) + "/index"
                    if not os.path.exists(os.path.join(ZH_DOC_PATH, url + ".md")):
                        url = sentence.split("$")[1].replace(self.file_path + "/", "").strip().lstrip() + "/index"
                    if not os.path.exists(os.path.join(ZH_DOC_PATH, url + ".md")):
                        try:
                            url = find_dir(sentence.split("$")[1].split("/")[-1], ZH_DOC_PATH).replace(ZH_DOC_PATH, "")[
                                  1:]
                        except Exception:
                            url, name = use_origin_url(sentence.split("$")[1])
                            return self.renderer.super_link(url, name)
                name = list(filter(lambda x: x["type"] == "heading" and x["level"] == 1, mistune.BlockLexer().parse(
                    open(os.path.join(ZH_DOC_PATH, url + ".md"), encoding="utf-8").read())))[0]["text"]
                url = "../" + url + ".html"
                if param != "":
                    url += "#" + param
            return self.renderer.super_link(url, name)
        except Exception:
            print(sentence)
            return sentence


class Template:
    def __init__(self, content, clazz, name):
        soup = bs(content, "html5lib")
        self.title = soup.h1.get_text()
        self.clazz = clazz
        self.en_name = name
        self.content = content
        self.is_left_nav = os.path.exists(os.path.join(ZH_DOC_PATH, clazz, "leftnav_files"))
        self.template = open(TEMPLATE).read()

    def left_nav(self):
        if self.is_left_nav:
            return open(os.path.join(ZH_DOC_PATH, self.clazz, "leftnav_files"), encoding="utf-8").read()
        else:
            return ""

    def render(self):
        return self.template.format(title=self.title, content=self.content, left_nav=self.left_nav())


def render(markdown: str, path: str, name: str) -> str:
    md_renderer = CustomRenderer(escape=False, hard_wrap=True)
    md_inline_lexer = CustomInlineLexer(md_renderer)
    md_inline_lexer.enable_super_link()
    md_inline_lexer.file_path = path
    md_parse = mistune.Markdown(renderer=md_renderer, inline=md_inline_lexer, hard_wrap=False)
    content = md_parse(markdown)
    html_renderer = Template(content=content, clazz=path, name=name)
    return html_renderer.render()


if __name__ == "__main__":
    black_list = [".git", "leftnav_files", "README.txt", "README.md"]
    for (root, dirs, files) in os.walk(ZH_DOC_PATH):
        new_root = root.replace(ZH_DOC_PATH, GENERATE_PATH, 1)
        if not os.path.exists(new_root):
            os.mkdir(new_root)

        for d in dirs:
            d = os.path.join(new_root, d)
            if not os.path.exists(d):
                os.mkdir(d)

        for f in tqdm(files):
            if f not in black_list:
                (shot_name, extension) = os.path.splitext(f)
                old_path = os.path.join(root, f)
                if root == os.path.join(ZH_DOC_PATH, "images"):
                    new_name = shot_name + extension
                else:
                    new_name = shot_name + ".html"
                new_path = os.path.join(new_root, new_name)
                if new_name[-4:] == "html":
                    open(new_path, 'w', encoding="utf-8").write(
                        render(open(old_path, encoding="utf-8").read(), os.path.split(root)[1], name=shot_name))
                else:
                    open(new_path, 'wb').write(open(old_path, "rb").read())
