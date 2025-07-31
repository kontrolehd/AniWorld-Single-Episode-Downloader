import base64
import json
import re
import requests
import random
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


DEFAULT_REQUEST_TIMEOUT = 30
RANDOM_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
LULUVDO_USER_AGENT = (
    "Mozilla/5.0 (Android 15; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0"
)


def get_direct_link_from_vidoza(embeded_vidoza_link: str) -> str:
    try:
        resp = requests.get(
            embeded_vidoza_link,
            headers={"User-Agent": RANDOM_USER_AGENT},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as err:
        raise ValueError(f"Failed to fetch Vidoza page: {err}") from err

    html_content = resp.text
    match = re.search(r'sourcesCode:\s*"([^"]+)"', html_content)
    if match:
        return match.group(1)

    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup.find_all("script", string=True):
        if script.string and "sourcesCode:" in script.string:
            match = re.search(r'sourcesCode:\s*"([^"]+)"', script.string)
            if match:
                return match.group(1)

    raise ValueError("No direct link found in Vidoza page.")


def get_direct_link_from_vidmoly(embeded_vidmoly_link: str) -> str:
    try:
        resp = requests.get(
            embeded_vidmoly_link,
            headers={"User-Agent": RANDOM_USER_AGENT},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as err:
        raise ValueError(f"Failed to fetch Vidmoly page: {err}") from err

    html = resp.text
    match = re.search(r'file:\s*"(https?://[^\"]+)"', html)
    if match:
        return match.group(1)

    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", string=True):
        if script.string:
            match = re.search(r'file:\s*"(https?://[^\"]+)"', script.string)
            if match:
                return match.group(1)

    raise ValueError("No direct link found in Vidmoly page.")


def get_direct_link_from_loadx(embeded_loadx_link: str) -> str:
    def _validate_loadx_url(url: str) -> str:
        if not url or not url.strip():
            raise ValueError("LoadX URL cannot be empty")
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Invalid URL format - must start with http:// or https://")
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("Invalid URL format - missing domain")
        return url

    def _make_request(url: str, method: str = "GET", headers=None, allow_redirects=True):
        try:
            if method.upper() == "HEAD":
                response = requests.head(
                    url,
                    allow_redirects=allow_redirects,
                    verify=False,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                    headers=headers or {},
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=headers or {},
                    verify=False,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                )
            else:
                response = requests.get(
                    url,
                    headers=headers or {},
                    verify=False,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                )
            response.raise_for_status()
            return response
        except requests.RequestException as err:
            raise ValueError(f"Failed to fetch URL: {err}") from err

    def _extract_id_hash_from_url(url: str):
        parsed_url = urlparse(url)
        parts = parsed_url.path.split("/")
        if len(parts) < 3:
            raise ValueError("Invalid LoadX URL structure")
        id_hash = parts[2]
        host = parsed_url.netloc
        if not id_hash or not host:
            raise ValueError("Invalid LoadX URL")
        return id_hash, host

    def _parse_video_response(text: str) -> str:
        try:
            data = json.loads(text)
            video_url = data.get("videoSource")
            if not video_url:
                raise ValueError("No video source found in response")
            return video_url.strip()
        except Exception as err:
            raise ValueError(f"Invalid JSON response: {err}") from err

    validated_url = _validate_loadx_url(embeded_loadx_link)
    head_resp = _make_request(validated_url, method="HEAD", allow_redirects=True)
    id_hash, host = _extract_id_hash_from_url(head_resp.url)
    post_url = f"https://{host}/player/index.php?data={id_hash}&do=getVideo"
    api_resp = _make_request(post_url, method="POST", headers={"X-Requested-With": "XMLHttpRequest"})
    return _parse_video_response(api_resp.text)


def get_direct_link_from_luluvdo(embeded_luluvdo_link: str) -> str:
    def _validate_luluvdo_url(url: str) -> str:
        if not url or not url.strip():
            raise ValueError("LuluVDO URL cannot be empty")
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Invalid URL format - must start with http:// or https://")
        parsed_url = urlparse(url)
        if not parsed_url.netloc or "luluvdo.com" not in parsed_url.netloc.lower():
            raise ValueError("URL must be from luluvdo.com")
        return url

    def _extract_luluvdo_id(url: str) -> str:
        parts = url.split("/")
        if not parts:
            raise ValueError("Invalid URL structure")
        code = parts[-1]
        if not code:
            raise ValueError("No ID found in URL")
        if "?" in code:
            code = code.split("?")[0]
        if not code:
            raise ValueError("Empty ID after processing")
        return code

    def _build_embed_url(luluvdo_id: str) -> str:
        return f"https://luluvdo.com/dl?op=embed&file_code={luluvdo_id}&embed=1&referer=luluvdo.com&adb=0"

    def _make_request(url: str, headers: dict) -> requests.Response:
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=DEFAULT_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as err:
            raise ValueError(f"Failed to fetch URL: {err}") from err

    def _extract_video_url(text: str) -> str:
        match = re.search(r'file:\s*"([^"]+)"', text)
        if not match:
            raise ValueError("No video URL found in response")
        return match.group(1).strip()

    validated = _validate_luluvdo_url(embeded_luluvdo_link)
    luluvdo_id = _extract_luluvdo_id(validated)
    embed_url = _build_embed_url(luluvdo_id)
    headers = {
        "Origin": "https://luluvdo.com",
        "Referer": "https://luluvdo.com/",
        "User-Agent": LULUVDO_USER_AGENT,
    }
    resp = _make_request(embed_url, headers)
    return _extract_video_url(resp.text)


def get_direct_link_from_filemoon(embeded_filemoon_link: str) -> str:
    if not embeded_filemoon_link:
        raise ValueError("Embed URL cannot be empty")

    download_url = embeded_filemoon_link.replace("/e/", "/d/") if "/e/" in embeded_filemoon_link else embeded_filemoon_link

    def _make_request(url: str, headers=None):
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=DEFAULT_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as err:
            raise ValueError(f"Failed to fetch URL: {err}") from err

    page = _make_request(download_url, headers={"User-Agent": RANDOM_USER_AGENT})
    soup = BeautifulSoup(page.text, "html.parser")
    iframe = soup.find("iframe")
    if not iframe or not iframe.get("src"):
        raise ValueError("No iframe found on Filemoon page")
    iframe_url = iframe.get("src")

    headers = {
        "Referer": "https://filemoon.to",
        "User-Agent": RANDOM_USER_AGENT,
    }
    iframe_resp = _make_request(iframe_url, headers=headers)
    content = iframe_resp.text
    match = re.search(r'file:\s*"([^"]+)"', content)
    if not match:
        raise ValueError("No file URL found in Filemoon iframe")
    return match.group(1).strip()


def get_direct_link_from_doodstream(embeded_doodstream_link: str) -> str:
    if not embeded_doodstream_link:
        raise ValueError("Embed URL cannot be empty")

    def _get_headers() -> dict:
        return {
            "User-Agent": RANDOM_USER_AGENT,
            "Referer": "https://dood.li/",
        }

    def _make_request(url: str, headers: dict):
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=DEFAULT_REQUEST_TIMEOUT,
                verify=False,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as err:
            raise ValueError(f"Request failed for {url}: {err}") from err

    def _extract_data(pattern: str, content: str):
        match = re.search(pattern, content)
        return match.group(1) if match else None

    def _generate_random_string(length: int = 10) -> str:
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.choice(chars) for _ in range(length))

    headers = _get_headers()
    resp = _make_request(embeded_doodstream_link, headers)
    text = resp.text

    pass_md5_pattern = r"\$\.get\('([^']*\/pass_md5\/[^']*)'"
    token_pattern = r"token=([a-zA-Z0-9]+)"
    pass_md5_url = _extract_data(pass_md5_pattern, text)
    if not pass_md5_url:
        raise ValueError("pass_md5 URL not found in Doodstream page")
    if not pass_md5_url.startswith("http"):
        pass_md5_url = urljoin("https://dood.li", pass_md5_url)
    token = _extract_data(token_pattern, text)
    if not token:
        raise ValueError("Token not found in Doodstream page")

    md5_resp = _make_request(pass_md5_url, headers)
    base_url = md5_resp.text.strip()
    if not base_url:
        raise ValueError("Empty base URL received from Doodstream")

    random_str = _generate_random_string(10)
    expiry = int(time.time())
    return f"{base_url}{random_str}?token={token}&expiry={expiry}"


def get_direct_link_from_voe(embeded_voe_link: str) -> str:
    def shift_letters(input_str: str) -> str:
        result = []
        for c in input_str:
            code = ord(c)
            if 65 <= code <= 90:
                code = (code - 65 + 13) % 26 + 65
            elif 97 <= code <= 122:
                code = (code - 97 + 13) % 26 + 97
            result.append(chr(code))
        return "".join(result)

    def replace_junk(s: str) -> str:
        junk_parts = ["@$", "^^", "~@", "%?", "*~", "!!", "#&"]
        for part in junk_parts:
            s = s.replace(part, "_")
        return s

    def shift_back(s: str, n: int) -> str:
        return "".join(chr(ord(c) - n) for c in s)

    def decode_voe_string(encoded: str):
        try:
            step1 = shift_letters(encoded)
            step2 = replace_junk(step1).replace("_", "")
            step3 = base64.b64decode(step2).decode()
            step4 = shift_back(step3, 3)
            step5 = base64.b64decode(step4[::-1]).decode()
            return json.loads(step5)
        except Exception as err:
            raise ValueError(f"Failed to decode VOE string: {err}") from err

    try:
        resp = requests.get(
            embeded_voe_link,
            headers={"User-Agent": RANDOM_USER_AGENT},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as err:
        raise ValueError(f"Failed to fetch VOE page: {err}") from err

    match = re.search(r"https?://[^'\"<>]+", resp.text)
    if not match:
        raise ValueError("No redirect URL found in VOE response.")
    redirect_url = match.group(0)

    try:
        with requests.get(
            redirect_url,
            headers={"User-Agent": RANDOM_USER_AGENT},
            timeout=DEFAULT_REQUEST_TIMEOUT,
        ) as r:
            r.raise_for_status()
            html = r.text
    except requests.RequestException as err:
        raise ValueError(f"Failed to follow redirect: {err}") from err

    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", type="application/json")
    if script and script.text:
        try:
            decoded = decode_voe_string(script.text[2:-2])
            source = decoded.get("source")
            if source:
                return source
        except Exception:
            pass

    b64_match = re.search(r"var a168c='([^']+)'", html)
    if b64_match:
        try:
            decoded = base64.b64decode(b64_match.group(1)).decode()[::-1]
            source = json.loads(decoded).get("source")
            if source:
                return source
        except Exception:
            pass

    hls_match = re.search(r"'hls': '(?P<hls>[^']+)'", html)
    if hls_match:
        try:
            return base64.b64decode(hls_match.group("hls")).decode()
        except Exception:
            pass

    raise ValueError("No video source found in VOE page.")
