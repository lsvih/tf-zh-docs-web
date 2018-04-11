import os
import re
import sys

import mistune
import requests
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
        if string == _path.split("/")[-1]:
            return _path
    raise Exception("couldn't find file: %s" % (string))


def use_origin_url(key):
    dic = {"xla": ("https://www.tensorflow.org/performance/xla/", "XLA 编译器")}
    return dic.get(key)


class CustomRenderer(mistune.Renderer):
    def super_link(self, link, text):
        return '<a href="%s">%s</a>' % (link, text)

    def table(self, header, body):
        return ('<div class="table-wrapper"><table>\n<thead>%s</thead>\n'
                '<tbody>\n%s</tbody>\n</table></div>\n') % (header, body)


class CustomBlockLexer(mistune.BlockLexer):
    default_rules = [
        'newline', 'hrule', 'list_block', 'fences', 'heading',
        'nptable', 'lheading', 'block_quote',
        'block_code', 'block_html', 'def_links',
        'def_footnotes', 'table', 'paragraph', 'text'
    ]


class CustomInlineLexer(mistune.InlineLexer):
    def __init__(self, renderer, **kwargs):
        super().__init__(renderer, **kwargs)
        self.file_path = None
        self.domain = None

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
                url = "//" + self.domain + "/" + url + ".html"
                if param != "":
                    url += "#" + param
            return self.renderer.super_link(url, name)
        except Exception:
            print(sentence)
            return sentence


class Template:
    def __init__(self, content, clazz, name, domain):
        soup = bs(content, "html5lib")
        self.title = soup.h1.get_text()
        self.clazz = clazz
        self.en_name = name
        self.content = content
        self.domain = domain
        self.is_left_nav = os.path.exists(os.path.join(ZH_DOC_PATH, clazz, "leftnav_files"))
        self.template = open(TEMPLATE, encoding="utf-8").read()
        self.left_template = open(LEFT_NAV_TEMPLATE, encoding="utf-8").read()
        self.head_template = open(HEAD_NAV_TEMPLATE, encoding="utf-8").read()
        self.footer_template = open(FOOTER_TEMPLATE, encoding="utf-8").read()

    def left_nav(self) -> str:
        def _get_link(filename) -> str:
            filearr = filename.split(":")
            if len(filearr) == 2:
                return filearr[0]
            else:
                return filename

        def _get_title(filename) -> str:
            filearr = filename.split(":")
            if len(filearr) == 2:
                return filearr[1]
            else:
                return list(filter(lambda x: x["type"] == "heading" and x["level"] == 1, mistune.BlockLexer().parse(
                    open(os.path.join(ZH_DOC_PATH, self.clazz, filename), encoding="utf-8").read())))[0]["text"]

        nav = []
        sub_flag = False
        is_parent, get_parent_title = re.compile(r"#{3}"), re.compile(r"#{3}(.+?)\n")
        if self.is_left_nav:
            origin = open(os.path.join(ZH_DOC_PATH, self.clazz, "leftnav_files"), encoding="utf-8").readlines()
            for line in origin:
                if is_parent.match(line):
                    sub_flag = True
                    nav.append({"type": "parent", "title": get_parent_title.match(line).group(1).replace("\n", ""),
                                "sub_class": []})
                elif line == "\n" or line == ">>>\n":
                    sub_flag = False
                else:
                    if sub_flag:
                        nav[-1]["sub_class"].append({"link": _get_link(line.replace("\n", ""))})
                    else:
                        nav.append({"type": "child", "link": _get_link(line.replace("\n", ""))})
            # Generated Navigation Tree, find title for each document.
            for i, ele in enumerate(nav):
                if ele["type"] == "child":
                    nav[i]["title"] = _get_title(ele["link"])
                    nav[i]["link"] = "//" + self.domain + "/" + self.clazz + "/" + ele["link"].replace(".md", ".html")
                else:
                    for j, sub_ele in enumerate(ele["sub_class"]):
                        nav[i]["sub_class"][j]["title"] = _get_title(sub_ele["link"])
                        nav[i]["sub_class"][j]["link"] = "//" + self.domain + "/" + self.clazz + "/" + sub_ele[
                            "link"].replace(".md",
                                            ".html")
            return self.render_left_nav(nav)
        else:
            return ""

    def render_left_nav(self, nav: list) -> str:
        return self.left_template.format(data=nav)

    def build_header(self):
        def _get_path_title(path) -> str:
            return list(filter(lambda x: x["type"] == "heading" and x["level"] == 1, mistune.BlockLexer().parse(
                open(os.path.join(ZH_DOC_PATH, path, "index.md"), encoding="utf-8").read())))[0]["text"]

        return [{"link": "//%s/%s/index.html" % (domain, sub_path), "name": _get_path_title(sub_path),
                 "selected": int(sub_path == self.clazz)} for
                sub_path in os.listdir(ZH_DOC_PATH) if
                os.path.exists(os.path.join(ZH_DOC_PATH, sub_path, "index.md"))]

    def render_head_nav(self) -> str:
        return self.head_template.format(data=self.build_header())

    def render_footer(self) -> str:
        def _get_contributors(url: str) -> str:
            contributor_list = [{commit["author"]["login"]: commit["author"]["avatar_url"]}
                                if commit["author"] is not None else
                                {commit["commit"]["author"]["name"]: ""}
                                for commit in requests.get(
                    url="%s/commits?path=%s" % (GIT_API, url),
                    headers={'Authorization': 'token %s' % open("secret").read()}).json()]
            return str([i for n, i in enumerate(contributor_list) if i not in contributor_list[n + 1:]])

        file_path = os.path.join(ZH_DOC_PATH, "%s/%s.md" % (self.clazz, self.en_name))
        if not os.path.exists(file_path):
            file_path = find_dir("%s" % self.clazz, ZH_DOC_PATH) + "/" + self.en_name + ".md"
        url = REMOTE_ZH_DOC_URL + file_path[1:]
        path = file_path.replace(ZH_DOC_PATH, "")
        return self.footer_template.format(url=url, domain=self.domain, contributors=_get_contributors(path))

    def render(self):
        return self.template.format(title=self.title, content=self.content, left_nav=self.left_nav(),
                                    head_nav=self.render_head_nav(), domain=self.domain, footer=self.render_footer())


def render(markdown: str, path: str, name: str, domain: str) -> str:
    md_renderer = CustomRenderer(escape=False, hard_wrap=True)
    md_block_lexer = CustomBlockLexer()
    md_inline_lexer = CustomInlineLexer(md_renderer)
    md_inline_lexer.enable_super_link()
    md_inline_lexer.file_path = path
    md_inline_lexer.domain = domain
    md_parse = mistune.Markdown(renderer=md_renderer, inline=md_inline_lexer, block=md_block_lexer, hard_wrap=False)
    content = md_parse(markdown)
    html_renderer = Template(content=content, clazz=path, name=name, domain=domain)
    return html_renderer.render()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate.py your-domain")
        exit()
    domain = sys.argv[1]
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
                (short_name, extension) = os.path.splitext(f)
                old_path = os.path.join(root, f)
                if root == os.path.join(ZH_DOC_PATH, "images"):
                    new_name = short_name + extension
                else:
                    new_name = short_name + ".html"
                new_path = os.path.join(new_root, new_name)
                if new_name[-4:] == "html":
                    open(new_path, 'w', encoding="utf-8").write(
                        render(open(old_path, encoding="utf-8").read(), os.path.split(root)[1], name=short_name,
                               domain=domain))
                else:
                    open(new_path, 'wb').write(open(old_path, "rb").read())
    os.system("cp -r assets dist/")
    print("Done!")
