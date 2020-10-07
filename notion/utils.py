import os
import uuid
from datetime import datetime
from typing import Union, Iterable, Any
from urllib.parse import urlparse, parse_qs, quote_plus, unquote_plus

import requests
from bs4 import BeautifulSoup
from slugify import slugify as _dash_slugify

from notion.settings import (
    BASE_URL,
    SIGNED_URL_PREFIX,
    S3_URL_PREFIX,
    EMBED_API_URL,
)


class InvalidNotionIdentifier(Exception):
    """
    Invalid Notion Identifier was found.
    """

    pass


def to_list(value) -> list:
    """
    Wrap value in list if it's not already in a list.


    Arguments
    ---------
    value : Any
        Value to wrap in list.


    Returns
    -------
    list
        List with value inside.
    """
    return value if isinstance(value, list) else [value]


def now() -> int:
    """
    Get UNIX-style time since epoch in seconds.


    Returns
    -------
    int
        Time since epoch in seconds.
    """
    return int(datetime.now().timestamp() * 1000)


def human_size(path: str, divider: int = 1024) -> str:
    """
    Get human readable file size.


    Arguments
    ---------
    path : str
        Path to the file.

    divider : int, optional
        Divider used for calculations, use 1000 or 1024.
        Defaults to 1024.


    Returns
    -------
    str
        Converted size.
    """
    size, divider = os.path.getsize(path), float(divider)
    size = size / divider if size < divider else size

    for unit in ("KB", "KB", "MB", "GB", "TB"):
        if abs(size) < divider:
            return f"{size:.1f}{unit}"
        size /= divider

    return str(size)


def extract_id(url_or_id: str) -> str:
    """
    Extract the block/page ID from a Notion.so URL.

    If it's a bare page URL, it will be the ID of the page.
    If there's a hash with a block ID in it (from clicking "Copy Link")
    on a block in a page), it will instead be the ID of that block.
    If it's already in ID format, it will be passed right through.


    Arguments
    ---------
    url_or_id : str
        Link to block or its ID.


    Raises
    ------
    InvalidNotionIdentifier
        Raised when `url_or_id` can't be converted to UUID.


    Returns
    -------
    str
        ID of the block.
    """
    original_url_or_id = url_or_id

    if url_or_id.startswith(BASE_URL):
        url_or_id = (
            url_or_id.split("#")[-1]
            .split("/")[-1]
            .split("&p=")[-1]
            .split("?")[0]
            .split("-")[-1]
        )

    try:
        return str(uuid.UUID(url_or_id))
    except ValueError:
        raise InvalidNotionIdentifier(original_url_or_id)


def get_embed_link(source_url: str, client) -> str:
    """
    Get embed link.


    Arguments
    ---------
    source_url : str
        Source URL from which the embedded link will be extracted.

    client : NotionClient
        Client used for sending the actual request.


    Returns
    -------
    str
        Extracted link.
    """
    data = client.get(f"{EMBED_API_URL}&url={source_url}").json()

    if "html" not in data:
        return source_url

    # TODO: replace BS4 with built in solution
    url = list(BeautifulSoup(data["html"], "html.parser").children)[0]["src"]

    return parse_qs(urlparse(url).query)["src"][0]


def add_signed_prefix_as_needed(url: str, client=None) -> str:
    """
    Utility function for adding signed prefix to URL.


    Arguments
    ---------
    url : str
        URL to operate on.

    client : NotionClient, optional
        It's used for making wrapped requests via
        initialized requests.Session object.
        Defaults to None.


    Returns
    -------
    str
        Prefixed URL.
    """
    if not url:
        return ""

    if url.startswith(S3_URL_PREFIX):
        path, query = url.split("?")
        url = f"{SIGNED_URL_PREFIX}{quote_plus(path)}?{query}"

        if client:
            url = client.session.head(url).headers.get("Location")

    return url


def remove_signed_prefix_as_needed(url: str) -> str:
    """
    Utility function for removing signed prefix from URL.


    Arguments
    ---------
    url : str
        URL to operate on.


    Returns
    -------
    str
        Non-prefixed URL.
    """
    if url.startswith(SIGNED_URL_PREFIX):
        url = unquote_plus(url[len(S3_URL_PREFIX) :])

    return url or ""


def slugify(text: str) -> str:
    """
    Convert text to computer-friendly simplified form.


    Arguments
    ---------
    text : str
        String to operate on.


    Returns
    -------
    str
        Converted string.
    """
    return _dash_slugify(text).replace("-", "_")


def get_by_path(path: Union[Iterable, str], obj: Any, default: Any = None) -> Any:
    """
    Get value from object's key by dotted path (i.e. "path.to.some.key").


    Arguments
    ---------
    path : list or str
        Path in string form or as list elements.

    obj : Any
        Object to traverse.

    default: Any, optional
        Default value if key was invalid.
        Defaults to None.


    Returns
    -------
    Any
        Value stored under specified key or default value.
    """
    if isinstance(path, str):
        path = path.split(".")

    value = obj

    # try to traverse down the sequence of keys defined
    # in the path, to get the target value if it exists
    try:
        for key in path:
            if isinstance(value, list):
                key = int(key)
            value = value[key]
    except (KeyError, TypeError, IndexError):
        value = default

    return value
