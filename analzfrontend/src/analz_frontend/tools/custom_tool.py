from crewai.tools import BaseTool
from typing import Type, Optional, ClassVar, Any
from pydantic import BaseModel, Field
import httpx
import re
import json
from urllib.parse import urljoin, urlparse


# ─────────────────────────────────────────────
# Tool 1: Raw HTML + CSS + JS Fetcher
# ─────────────────────────────────────────────

class FetchFrontendInput(BaseModel):
    url: str = Field(..., description="The full URL of the website to fetch and analyze")


class FetchFrontendSourceTool(BaseTool):
    name: str = "fetch_frontend_source"
    description: str = (
        "Fetches the raw HTML source of a webpage and attempts to inline "
        "linked CSS and JS file contents. Returns a combined source string "
        "for deep frontend analysis including all styles and scripts."
    )
    args_schema: Type[BaseModel] = FetchFrontendInput

    def _run(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        try:
            resp = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            return f"ERROR fetching {url}: {e}"

        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        result_parts = [f"=== HTML SOURCE: {url} ===\n{html[:3000]}\n"]

        # Extract and fetch linked CSS files
        css_links = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']', html)
        for href in css_links[:3]:  # limit to 3 CSS files
            css_url = href if href.startswith("http") else urljoin(base_url, href)
            try:
                css_resp = httpx.get(css_url, headers=headers, timeout=10, follow_redirects=True)
                result_parts.append(f"\n=== CSS FILE: {css_url} ===\n{css_resp.text[:2000]}\n")
            except Exception as e:
                result_parts.append(f"\n=== CSS FILE: {css_url} === ERROR: {e}\n")

        # Extract and fetch linked JS files (first 3 non-vendor)
        js_links = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
        non_vendor = [j for j in js_links if not any(v in j for v in ["analytics", "gtag", "fbq", "hotjar"])]
        for src in non_vendor[:2]:
            js_url = src if src.startswith("http") else urljoin(base_url, src)
            try:
                js_resp = httpx.get(js_url, headers=headers, timeout=10, follow_redirects=True)
                result_parts.append(f"\n=== JS FILE: {js_url} ===\n{js_resp.text[:2000]}\n")
            except Exception as e:
                result_parts.append(f"\n=== JS FILE: {js_url} === ERROR: {e}\n")

        return "\n".join(result_parts)


# ─────────────────────────────────────────────
# Tool 2: Library & Framework Fingerprinter
# ─────────────────────────────────────────────

class FingerprintInput(BaseModel):
    html_source: Any = Field(..., description="Raw HTML source string to fingerprint. Must be a plain string of HTML content.")


class LibraryFingerprintTool(BaseTool):
    name: str = "fingerprint_libraries"
    description: str = (
        "Analyzes raw HTML source to detect frontend frameworks, CSS frameworks, "
        "animation libraries, and bundler signatures. Returns a structured "
        "fingerprint of the tech stack."
    )
    args_schema: Type[BaseModel] = FingerprintInput

    # Known signatures: (pattern, human-readable label)
    SIGNATURES: ClassVar[dict[str, str]] = {
        # Frameworks
        "__NEXT_DATA__": "Next.js",
        "__nuxt": "Nuxt.js",
        "astro-island": "Astro",
        "_app.svelte": "SvelteKit",
        "remix-context": "Remix",
        "gatsby-focus-wrapper": "Gatsby",
        # CSS frameworks
        "tailwind": "Tailwind CSS",
        "data-tw": "Tailwind CSS",
        "styled-components": "Styled Components",
        "__emotion": "Emotion CSS",
        "css-modules": "CSS Modules",
        # Animation libraries
        "gsap": "GSAP",
        "ScrollTrigger": "GSAP ScrollTrigger",
        "framer-motion": "Framer Motion",
        "lenis": "Lenis (smooth scroll)",
        "barba.js": "Barba.js (page transitions)",
        "barba-namespace": "Barba.js",
        "motion": "Motion One",
        "anime.js": "Anime.js",
        # 3D / Canvas
        "three.js": "Three.js",
        "THREE": "Three.js",
        "p5.js": "p5.js",
        "pixi": "PixiJS",
        "webgl": "WebGL",
        # Misc
        "locomotive-scroll": "Locomotive Scroll",
        "swiper": "Swiper.js",
        "splitting": "Splitting.js (text)",
    }

    def _run(self, html_source: Any) -> str:
        # Defensively coerce to string in case LLM passes an object
        if isinstance(html_source, dict):
            html_source = json.dumps(html_source)
        elif not isinstance(html_source, str):
            html_source = str(html_source)
        found = []
        lower = html_source.lower()

        for signature, label in self.SIGNATURES.items():
            if signature.lower() in lower and label not in found:
                found.append(label)

        # Detect experimental CSS APIs
        experimental = []
        if "@layer" in html_source:
            experimental.append("CSS @layer (cascade layers)")
        if "container-type" in html_source or "@container" in html_source:
            experimental.append("CSS Container Queries")
        if ":has(" in html_source:
            experimental.append("CSS :has() selector")
        if "@property" in html_source:
            experimental.append("CSS @property (Houdini)")
        if "scroll-timeline" in lower or "animation-timeline" in lower:
            experimental.append("Scroll-Driven Animations (CSS)")
        if "view-transition" in lower:
            experimental.append("View Transitions API")
        if "paint-worklet" in lower:
            experimental.append("CSS Houdini Paint Worklet")
        if "font-variation-settings" in lower:
            experimental.append("Variable Fonts")

        output = []
        if found:
            output.append("## Detected Libraries & Frameworks\n" + "\n".join(f"- {lib}" for lib in found))
        else:
            output.append("## Detected Libraries & Frameworks\nNone clearly detected — may use custom/bundled code.")

        if experimental:
            output.append("\n## Experimental / Modern CSS APIs\n" + "\n".join(f"- {api}" for api in experimental))

        return "\n".join(output)


# ─────────────────────────────────────────────
# Tool 3: CSS Pattern Extractor
# ─────────────────────────────────────────────

class CSSPatternInput(BaseModel):
    css_source: Any = Field(..., description="Raw CSS source string to analyze for unique patterns. Must be a plain string of CSS content.")


class CSSPatternExtractorTool(BaseTool):
    name: str = "extract_css_patterns"
    description: str = (
        "Extracts notable, unusual, or modern CSS patterns from raw CSS source. "
        "Looks for advanced layout, animation, custom property architecture, "
        "and rare property usage."
    )
    args_schema: Type[BaseModel] = CSSPatternInput

    def _run(self, css_source: Any) -> str:
        # Defensively coerce to string in case LLM passes an object
        if isinstance(css_source, dict):
            css_source = json.dumps(css_source)
        elif not isinstance(css_source, str):
            css_source = str(css_source)
        findings = []
        css = css_source.lower()

        checks = [
            ("clip-path", "clip-path shapes for non-rectangular layouts"),
            ("shape-outside", "shape-outside for text wrapping around shapes"),
            ("mask-image", "CSS mask-image for creative reveals/effects"),
            ("mix-blend-mode", "mix-blend-mode for layer blending effects"),
            ("backdrop-filter", "backdrop-filter (blur/glass effects)"),
            ("perspective", "CSS 3D perspective transforms"),
            ("counter-reset", "CSS counters for auto-numbering"),
            ("writing-mode", "writing-mode (vertical text layouts)"),
            ("overscroll-behavior", "overscroll-behavior (scroll chaining control)"),
            ("scroll-snap", "CSS Scroll Snap for controlled scrolling"),
            ("grid-template-areas", "Named grid template areas layout"),
            ("subgrid", "CSS Subgrid for nested grid alignment"),
            ("conic-gradient", "conic-gradient for pie charts / color wheels"),
            ("@keyframes", "Custom CSS animations via @keyframes"),
            ("will-change", "will-change performance hints"),
            ("font-feature-settings", "Advanced OpenType font features"),
            ("ch", "ch units (character-based sizing)"),
            ("clamp(", "clamp() for fluid responsive typography"),
            ("var(--", "CSS custom properties (design token architecture)"),
        ]

        for pattern, description in checks:
            if pattern in css:
                # Try to extract a small snippet
                idx = css.find(pattern)
                snippet = css_source[max(0, idx - 20):idx + 60].strip().replace("\n", " ")
                findings.append(f"- **{description}**\n  `{snippet}...`")

        if findings:
            return "## Unique CSS Patterns Found\n\n" + "\n\n".join(findings)
        return "## Unique CSS Patterns\nNo strongly unusual patterns detected in provided CSS."