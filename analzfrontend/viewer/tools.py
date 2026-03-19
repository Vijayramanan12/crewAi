'''Viewer tool wrappers for frontend analysis.'''

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from analz_frontend.tools.custom_tool import (
    FetchFrontendSourceTool,
    LibraryFingerprintTool, 
    CSSPatternExtractorTool
)
from pathlib import Path
import hashlib
import json
import time
from datetime import timedelta

CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = timedelta(hours=1)

# ── Module Level Tools ──────────────────────────────
_FETCH = FetchFrontendSourceTool()
_FINGERPRINT = LibraryFingerprintTool()
_CSS = CSSPatternExtractorTool()

def cache_key(url: str, tool_name: str) -> str:
    hash_obj = hashlib.md5((url + tool_name).encode())
    return CACHE_DIR / f'{hash_obj.hexdigest()}.json'

def get_cached(url: str, tool_name: str):
    key = cache_key(url, tool_name)
    if key.exists():
        try:
            data = json.loads(key.read_text())
            if time.time() - data['timestamp'] < CACHE_TTL.total_seconds():
                return data['result']
        except Exception:
            return None
    return None

def set_cached(url: str, tool_name: str, result: str):
    key = cache_key(url, tool_name)
    data = {'timestamp': time.time(), 'result': result}
    key.write_text(json.dumps(data))

def clear_cache(url: str):
    """Remove all cached analysis for a given URL."""
    for tool_name in ['fetch', 'fingerprint', 'css']:
        key = cache_key(url, tool_name)
        if key.exists():
            key.unlink()

def analyze_url(url: str):
    """Run all 3 tools on URL, with caching. Returns dict of results."""
    results = {}
    
    # 1. Fetch source
    cached = get_cached(url, 'fetch')
    if cached:
        source = cached
    else:
        source = _FETCH._run(url)
        set_cached(url, 'fetch', source)
    
    # 2. Fingerprint
    cached_fp = get_cached(url, 'fingerprint')
    if cached_fp:
        fp_result = cached_fp
    else:
        fp_result = _FINGERPRINT._run(source)
        set_cached(url, 'fingerprint', fp_result)
    
    # 3. CSS patterns
    cached_css = get_cached(url, 'css')
    if cached_css:
        css_result = cached_css
    else:
        css_result = _CSS._run(source)
        set_cached(url, 'css', css_result)
    
    return {
        'source': source[:1500],
        'fingerprint': fp_result,
        'css_patterns': css_result
    }

