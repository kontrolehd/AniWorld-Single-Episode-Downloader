import os
import sys
import logging
import subprocess
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import base64
import json
import random
import re
import time


DEFAULT_REQUEST_TIMEOUT = 30
RANDOM_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

LULUVDO_USER_AGENT = (
    "Mozilla/5.0 (Android 15; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0"
)

PROVIDER_HEADERS_D: Dict[str, List[str]] = {
    "Vidmoly": ['Referer: "https://vidmoly.to"'],
    "Doodstream": ['Referer: "https://dood.li/"'],
    "VOE": [f"User-Agent: {RANDOM_USER_AGENT}"],
    "LoadX": ["Accept: */*"],
    "Filemoon": [
        f"User-Agent: {RANDOM_USER_AGENT}",
        'Referer: "https://filemoon.to"',
    ],
    "Luluvdo": [
        f"User-Agent: {LULUVDO_USER_AGENT}",
        "Accept-Language: de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        'Origin: "https://luluvdo.com"',
        'Referer: "https://luluvdo.com/"',
    ],
    "Vidoza": [],
    "SpeedFiles": [],
    "Streamtape": [],
    "Hanime": [],
}


def sanitize_filename(filename: str) -> str:
    invalid_chars = set('<>:"/\\|?*')
    return "".join(ch for ch in filename if ch not in invalid_chars)


def parse_providers_from_html(html_content: str, base_url: str) -> Dict[str, Dict[int, str]]:
    soup = BeautifulSoup(html_content, "html.parser")
    providers: Dict[str, Dict[int, str]] = {}

    episode_links = soup.find_all(
        "li", class_=lambda x: x and x.startswith("episodeLink")
    )

    if not episode_links:
        raise ValueError("No streaming providers found on the episode page.")

    for link in episode_links:
        provider_tag = link.find("h4")
        provider_name = provider_tag.get_text(strip=True) if provider_tag else None

        anchor = link.find("a", class_="watchEpisode")
        redirect_path = anchor.get("href") if anchor else None

        lang_key_str = link.get("data-lang-key")
        lang_key = int(lang_key_str) if lang_key_str and lang_key_str.isdigit() else None

        if provider_name and redirect_path and lang_key:
            redirect_url = urljoin(base_url, redirect_path)
            providers.setdefault(provider_name, {})[lang_key] = redirect_url

    if not providers:
        raise ValueError("Unable to extract providers from episode HTML.")

    return providers


def choose_provider(
    providers: Dict[str, Dict[int, str]],
    language_key: int = 3,
) -> Tuple[str, str]:
    for provider_name, lang_map in providers.items():
        if language_key in lang_map:
            return provider_name, lang_map[language_key]

    provider_name = next(iter(providers))
    first_lang_key = sorted(providers[provider_name].keys())[0]
    return provider_name, providers[provider_name][first_lang_key]


def follow_redirect_to_embed(redirect_url: str) -> str:
    resp = requests.get(
        redirect_url,
        headers={"User-Agent": RANDOM_USER_AGENT},
        timeout=DEFAULT_REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.url


def build_ytdl_command(
    direct_link: str, output_path: str, provider: str
) -> List[str]:
    cmd: List[str] = [
        "yt-dlp",
        direct_link,
        "--fragment-retries",
        "infinite",
        "--concurrent-fragments",
        "4",
        "-o",
        output_path,
        "--quiet",
        "--no-warnings",
        "--progress",
    ]

    for header in PROVIDER_HEADERS_D.get(provider, []):
        cmd.extend(["--add-header", header])

    return cmd


def run_download(cmd: List[str]) -> None:
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"yt-dlp failed with exit code {exc.returncode}") from exc


def derive_output_filename(episode_url: str) -> str:
    try:
        parsed = urlparse(episode_url)
        parts = [p for p in parsed.path.split("/") if p]
        slug = parts[-3]
        season_part = parts[-2]
        episode_part = parts[-1]
        season = int(season_part.split("-")[1])
        episode = int(episode_part.split("-")[1])
        title = sanitize_filename(slug)
        return f"{title}_S{season:02d}E{episode:02d}.mp4"
    except Exception:
        return sanitize_filename(os.path.basename(episode_url.rstrip("/"))) + ".mp4"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if len(sys.argv) != 2:
        print("Usage: python downloader.py <episode_url>")
        sys.exit(1)

    episode_url = sys.argv[1]
    logging.info(f"Fetching episode page: {episode_url}")
    try:
        resp = requests.get(
            episode_url,
            headers={"User-Agent": RANDOM_USER_AGENT},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as err:
        print(f"Error fetching episode URL: {err}")
        sys.exit(1)

    parsed = urlparse(episode_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    try:
        providers = parse_providers_from_html(resp.text, base_url)
    except Exception as err:
        print(f"Error parsing providers: {err}")
        sys.exit(1)

    provider_name, redirect_url = choose_provider(providers)
    logging.info(f"Selected provider: {provider_name} (redirect: {redirect_url})")

    try:
        embed_url = follow_redirect_to_embed(redirect_url)
    except Exception as err:
        print(f"Error obtaining embed URL: {err}")
        sys.exit(1)

    logging.info(f"Embed URL: {embed_url}")

    extractor_map = {
        "Vidoza": "extractors.get_direct_link_from_vidoza",
        "LoadX": "extractors.get_direct_link_from_loadx",
        "Luluvdo": "extractors.get_direct_link_from_luluvdo",
        "Filemoon": "extractors.get_direct_link_from_filemoon",
        "Doodstream": "extractors.get_direct_link_from_doodstream",
        "VOE": "extractors.get_direct_link_from_voe",
        "Vidmoly": "extractors.get_direct_link_from_vidmoly",
        "SpeedFiles": "extractors.get_direct_link_from_speedfiles",
    }

    if provider_name not in extractor_map:
        print(f"Provider '{provider_name}' is not supported.")
        sys.exit(1)

    extractor_func = None
    import importlib
    extractors = importlib.import_module("extractors")
    extractor_func = getattr(extractors, extractor_map[provider_name].split('.')[-1])

    try:
        direct_link = extractor_func(embed_url)
    except Exception as err:
        print(f"Error extracting direct link from provider '{provider_name}': {err}")
        sys.exit(1)

    logging.info(f"Direct video URL: {direct_link}")

    filename = derive_output_filename(episode_url)
    output_path = os.path.join(os.getcwd(), filename)
    logging.info(f"Downloading to {output_path}")

    cmd = build_ytdl_command(direct_link, output_path, provider_name)
    try:
        run_download(cmd)
        print(f"Download completed: {output_path}")
    except Exception as err:
        print(f"Download failed: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
