#!/usr/bin/env python
import datetime
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

import markdown
import markupsafe
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(__file__).resolve().parent
SITE_DIR = BASE_DIR / "site"
POSTS_DIR = BASE_DIR / "posts"
CONFIG_FILE = "config.toml"
FEED_FILENAME = "feed.rss"

env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def ensure_dir_exists(path):
    path.mkdir(parents=True, exist_ok=True)


def load_config():
    with open("config.yaml") as f:
        config = yaml.load(f, yaml.Loader)
    for post in config["posts"]:
        post["published_at"] = datetime.datetime.fromisoformat(post["published_at"])
        post["filename"] = Path(post["source"]).stem + ".html"
        post["url"] = "/posts/" + post["filename"]
        post["tags"] = [t.strip() for t in post.get("tags", [])]
    config["posts"].sort(key=lambda x: x["published_at"], reverse=True)
    return config


def generate_posts(site, posts):
    template = env.get_template("post.html")
    md = markdown.Markdown(
        extensions=[
            "meta",
            "fenced_code",
            "codehilite",
            "smarty",
            "toc",
    ])
    for post in posts:
        with open(POSTS_DIR / post["source"]) as f:
            post_html = md.convert(f.read())
        html = template.render(site=site, post=post, post_html=markupsafe.Markup(post_html))
        posts_dir = SITE_DIR / "posts"
        ensure_dir_exists(posts_dir)
        path = posts_dir / post["filename"]
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
    filename = SITE_DIR / "index.html"
    with open(filename, "w") as f:
        f.write(html)


def generate_feed(config, posts):
    template = env.get_template("feed.rss")
    xml = template.render(
        config=config,
        posts=posts,
        self_url=feed_url(config),
        last_pub_date=posts[0]["published_at"],
    )
    filename = SITE_DIR / FEED_FILENAME
    with open(filename, "w") as f:
        f.write(xml)


def generate_tag_pages(config, posts):
    tagged_posts = defaultdict(list)
    for post in posts:
        for tag in post["tags"]:
            tagged_posts[tag].append(post)
    template = env.get_template("index.html")
    for tag in tagged_posts:
        html = template.render(
            title=f'Posts tagged "{tag}"',
            description=f'Posts tagged "{tag}"',
            feed_url=feed_url(config),
            posts=tagged_posts[tag],
        )
        tags_dir = SITE_DIR / "tags"
        ensure_dir_exists(tags_dir)
        filename = tags_dir / f"{tag}.html"
        with open(filename, "w") as f:
            f.write(html)


def feed_url(config):
    return urljoin(config["url"], "feed.rss")


def copy_static_files():
    static_src_path = BASE_DIR / "static"
    static_dest_path = SITE_DIR / "static"
    shutil.copytree(static_src_path, static_dest_path, dirs_exist_ok=True)


def to_rfc_3339(iso_datetime):
    dt = datetime.datetime.fromisoformat(iso_datetime)
    return dt.isoformat("T") + "Z"


def to_canonical_url(url):
    return url + "/" if url[-1] != "/" else ""


def generate():
    print("Loading configuration")
    config = load_config()
    posts = config["posts"]
    site = config["site"]
    print("Generating posts...")
    for d in (SITE_DIR, POSTS_DIR):
        ensure_dir_exists(d)
    generate_posts(site, posts)
    print("Generating index page...")
    generate_index_page(site, posts)
    generate_tag_pages(site, posts)
    generate_feed(site, posts)
    print("Copying static files...")
    copy_static_files()


if __name__ == "__main__":
    generate()
