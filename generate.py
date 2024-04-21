#!/usr/bin/env python
from collections import defaultdict
import datetime
import os
import shutil
from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

import markdown
import toml
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markupsafe

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SITE_PATH = os.path.join(BASE_DIR, "site")
CONFIG_FILE = "config.toml"
FEED_FILENAME = "feed.rss"

env = Environment(
    loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")),
    autoescape=select_autoescape(["html", "xml"]),
)

try:
    os.makedirs(SITE_PATH)
except FileExistsError:
    pass


@dataclass
class Post:
    date: str
    description: str
    filename: str
    html: str
    tags: List[str]
    title: str
    url: str


def load_config():
    return toml.load(CONFIG_FILE)


def generate_posts(posts):
    for post in posts:
        template = env.get_template("post.html")
        html = template.render(
            post=post,
            post_html=markupsafe.Markup(post.html)
        )
        path = os.path.join(SITE_PATH, post.filename)
        with open(path, "w") as f:
            f.write(html)


def generate_index_page(config, posts):
    template = env.get_template("index.html")
    html = template.render(
        feed_url=feed_url(config),
        title=config["title"],
        description=config["description"],
        posts=posts,
    )
    filename = os.path.join(SITE_PATH, "index.html")
    with open(filename, "w") as f:
        f.write(html)


def generate_feed(config, posts):
    template = env.get_template("feed.rss")
    xml = template.render(
        config=config,
        posts=posts,
        self_url=feed_url(config),
        last_pub_date=posts[0].date,
    )
    filename = os.path.join(SITE_PATH, FEED_FILENAME)
    with open(filename, "w") as f:
        f.write(xml)


def generate_tag_pages(config, posts):
    tags_path = os.path.join(SITE_PATH, "tags")
    try:
        shutil.rmtree(tags_path)
    except FileNotFoundError:
        pass
    os.makedirs(tags_path)
    tagged_posts = defaultdict(list)
    for post in posts:
        for tag in post.tags:
            tagged_posts[tag].append(post)
    template = env.get_template("index.html")
    for tag in tagged_posts:
        html = template.render(
            title=f'Posts tagged "{tag}"',
            description=f'Posts tagged "{tag}"',
            feed_url=feed_url(config),
            posts=tagged_posts[tag],
        )
        filename = os.path.join(tags_path, f"{tag}.html")
        with open(filename, "w") as f:
            f.write(html)


def feed_url(config):
    return urljoin(config["url"], "feed.rss")


def copy_static_files():
    static_src_path = os.path.join(BASE_DIR, "static")
    static_dest_path = os.path.join(SITE_PATH, "static")
    try:
        shutil.rmtree(static_dest_path)
    except FileNotFoundError:
        pass
    shutil.copytree(static_src_path, static_dest_path)


def parse_markdown():
    for post in os.listdir(os.path.join(BASE_DIR, "posts")):
        md = markdown.Markdown(
            extensions=[
                "meta",
                "fenced_code",
                "codehilite",
                "smarty",
                "toc",
            ]
        )
        with open(os.path.join(BASE_DIR, "posts", post), "r") as f:
            post_html = md.convert(f.read())
        filename = os.path.splitext(os.path.basename(post))[0] + ".html"
        # pylint: disable=no-member
        description = (
            "".join(md.Meta["description"])
            if "description" in md.Meta
            else None
        )
        yield Post(
            date=to_rfc_3339(md.Meta["date"][0]),
            description=description,
            filename=filename,
            html=post_html,
            tags=[tag.strip() for tag in md.Meta.get("tags", [])],
            title="".join(md.Meta["title"]),
            url=f"/{filename}",
        )


def to_rfc_3339(iso_datetime):
    dt = datetime.datetime.fromisoformat(iso_datetime)
    return dt.isoformat("T") + "Z"


def to_canonical_url(url):
    return url + "/" if url[-1] != "/" else ""


def generate():
    print("Loading configuration")
    config = load_config()
    print("Generating posts...")
    posts = list(parse_markdown())
    posts.sort(key=lambda x: x.date, reverse=True)
    generate_posts(posts)
    print("Generating index page...")
    generate_index_page(config, posts)
    generate_tag_pages(config, posts)
    generate_feed(config, posts)
    print("Copying static files...")
    copy_static_files()


if __name__ == "__main__":
    generate()
