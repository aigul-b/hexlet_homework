from urllib.parse import urlparse, urlunparse

def normalize_url(url):
    parsed=urlparse(url)
    if not parsed.scheme and not parsed.netloc and parsed.path:
        parsed = urlparse(f"http://{url}")
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    return urlunparse((scheme, netloc, path, '', '', ''))