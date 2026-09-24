#!/usr/bin/env python3
"""
NASA Human Rating Guidance & OCHMO Standards Sitemap Generator
==============================================================
Recursively crawls https://www.nasa.gov/human-rating-guidance/ and associated
Office of the Chief Health and Medical Officer (OCHMO) reference libraries to produce
validated XML sitemaps and URL lists for Onyx ingestion.

Covers:
  1. All NASA OCHMO Technical Briefs (TB) and Medical Technical Briefs (MTB).
  2. NASA Handbooks (HIDH SP-2010-3407, HIDP TP-2014-218556, OCHMO-HB-004).
  3. NASA Standards (NASA-STD-3001 Vol 1 & 2, OCHMO-STD-1880.1 Aviation Standards).
  4. Work Instructions (M-QA-2021-025 Standards Revision Process).
  5. Decompression Sickness (DCS) Prebreathe Reference Library.
  6. Vehicle Acceleration Limits Library & Mishap Investigation Handbooks.
  7. NASA Integrated Medical Model (IMM) runs, CliFFs, and documentation.
"""

import os
import sys
import time
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse, quote
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

START_URL = "https://www.nasa.gov/human-rating-guidance/"
MINIMUM_EXPECTED_URLS = 450
MAX_WORKERS = 4
REQUEST_TIMEOUT = 25

CORE_SEEDS = [
    "https://www.nasa.gov/human-rating-guidance/",
    "https://www.nasa.gov/ochmo/hsa-standards/ochmo-technical-briefs/",
    "https://www.nasa.gov/human-integration-design-handbook/",
    "https://www.nasa.gov/ochmo/health-operations-and-oversight/hsa-standards/",
    "https://www.nasa.gov/ochmo/aerospace-medical-certification-standard/",
    "https://www.nasa.gov/ochmo/aviation-medical-certification-standards/",
    "https://www.nasa.gov/ochmo/hsa-standards/ochmo-independent-assessments/",
    "https://www.nasa.gov/reference/fundamentals-of-human-health/",
    "https://www.nasa.gov/reference/medical-operations-and-clinical-care/",
    "https://www.nasa.gov/reference/vehicle-systems-interfaces-structure-environmental-design/",
    "https://www.nasa.gov/reference/safety-history-contingency-mishaps/",
    "https://www.nasa.gov/reference/nasa-std-3001v1/",
    "https://www.nasa.gov/reference/nasa-std-3001v2/",
    "https://www.nasa.gov/ochmo/health-operations-and-oversight/chief-health-and-medical-officers-spaceflight-mishap-investigation-flight-surgeon-handbook/",
    "https://www.nasa.gov/ochmo/health-operations-and-oversight/vehicle-acceleration-limits-library/",
    "https://www.nasa.gov/ochmo/decompression-sickness-prebreathe-reference-library/",
    "https://www.nasa.gov/integrated-medical-model-documentation/",
    "https://www.nasa.gov/deep-space-exploration-imm-runs/",
    "https://www.nasa.gov/low-earth-orbit-imm-runs/",
    "https://www.nasa.gov/lunar-orbit-and-surface-imm-runs/",
    "https://www.nasa.gov/martian-orbit-and-surface-imm-runs/",
    "https://www.nasa.gov/ochmo/health-and-medical-systems/pre-postflight-medical-care/",
    "https://www.nasa.gov/ochmo/health-and-medical-systems/in-flight-medical-care/",
    "https://www.nasa.gov/ochmo/food-in-space/",
    "https://www.nasa.gov/ochmo/human-spaceflight-newsletters/",
    "https://www.nasa.gov/directorates/esdmd/hhp/human-spaceflight-and-aviation-standards/",
]

# Targeted path patterns for HTML pages to crawl
ALLOWED_PATH_PATTERNS = [
    "human-rating-guidance",
    "ochmo",
    "human-integration",
    "integrated-medical-model",
    "imm-runs",
    "reference/nasa-std-3001",
    "reference/fundamentals-of-human-health",
    "reference/medical-operations",
    "reference/vehicle-systems-interfaces",
    "reference/safety-history",
]

# Paths to skip
DISALLOWED_PATHS = [
    "/news-release/",
    "/newsletters/",
    "/image-of-the-day/",
    "/learning-resources/",
    "/careers/",
    "/social-media/",
    "/feed/",
    "/page/",
]


def create_resilient_session() -> requests.Session:
    """Create a requests session with automatic retries and exponential backoff."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def normalize_url(url: str) -> str:
    """Strip tracking query parameters and fragments, percent-encode path."""
    clean = url.split("?")[0].split("#")[0].strip()
    parsed = urlparse(clean)
    encoded_path = quote(parsed.path, safe="/:")
    return urlunparse((parsed.scheme, parsed.netloc, encoded_path, "", "", ""))


def is_target_html_url(url: str) -> bool:
    """Determine whether an HTML URL should be visited."""
    parsed = urlparse(url)
    if parsed.netloc not in ("www.nasa.gov", "nasa.gov"):
        return False
    path = parsed.path.lower()
    if any(dis in path for dis in DISALLOWED_PATHS):
        return False
    return any(p in path for p in ALLOWED_PATH_PATTERNS)


def crawl_human_rating_portal():
    print("=" * 70)
    print(" NASA Human Rating Guidance & OCHMO Standards Crawler")
    print(" (Resilient Rate-Throttled Engine with Zero-Churn Preservation)")
    print("=" * 70)

    session = create_resilient_session()

    visited_pages = set()
    to_visit = set(normalize_url(u) for u in CORE_SEEDS)
    discovered_pdfs = set()
    discovered_html_pages = set()

    def fetch_page(url: str):
        for attempt in range(1, 4):
            try:
                r = session.get(url, timeout=REQUEST_TIMEOUT)
                if r.status_code == 200:
                    return url, r.text
                elif r.status_code in [404, 410]:
                    print(f"[!] Page not found ({r.status_code}): {url}", file=sys.stderr)
                    return url, None
                else:
                    print(f"[!] Warning: HTTP {r.status_code} on {url} (attempt {attempt}/3)", file=sys.stderr)
            except Exception as e:
                print(f"[!] Error fetching {url} (attempt {attempt}/3): {e}", file=sys.stderr)
            time.sleep(1.0 * attempt)
        return url, None

    depth = 0
    max_depth = 3

    while to_visit and depth < max_depth:
        depth += 1
        current_batch = list(to_visit - visited_pages)
        to_visit = set()
        print(f"\n[*] Depth {depth}: Crawling {len(current_batch)} pages with {MAX_WORKERS} workers...", flush=True)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for url, html in executor.map(fetch_page, current_batch):
                visited_pages.add(url)
                if not html:
                    continue
                discovered_html_pages.add(url)

                for m in re.finditer(r'href=[\"\']([^\"\'#\s]+)[\"\']', html):
                    href = m.group(1)
                    full = urljoin(url, href)
                    clean = normalize_url(full)

                    if clean.lower().endswith(".pdf"):
                        # Ensure only official NASA host PDFs, excluding external repos like HRR
                        p = urlparse(clean)
                        if "nasa.gov" in p.netloc and "humanresearchroadmap" not in p.netloc:
                            discovered_pdfs.add(clean)
                    elif is_target_html_url(clean) and clean not in visited_pages:
                        to_visit.add(clean)

    print(f"\n[+] Crawl Complete!")
    print(f"    - Visited HTML Pages: {len(discovered_html_pages)}")
    print(f"    - Discovered PDFs:   {len(discovered_pdfs)}")

    return sorted(discovered_html_pages), sorted(discovered_pdfs)


def load_existing_lastmods(sitemap_path: str) -> dict[str, str]:
    """Load existing lastmod dates to prevent zero-change git churn."""
    existing = {}
    if os.path.exists(sitemap_path):
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for url_elem in root.findall("sm:url", ns):
                loc_elem = url_elem.find("sm:loc", ns)
                lastmod_elem = url_elem.find("sm:lastmod", ns)
                if loc_elem is not None and loc_elem.text and lastmod_elem is not None and lastmod_elem.text:
                    existing[loc_elem.text.strip()] = lastmod_elem.text.strip()
            print(f"[*] Loaded {len(existing)} existing lastmod timestamps from {sitemap_path}")
        except Exception as e:
            print(f"[!] Warning reading existing lastmod timestamps: {e}")

    # Fallback to git history if current file is suspiciously pruned
    if len(existing) < MINIMUM_EXPECTED_URLS:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cmd = ["git", "-C", script_dir, "show", "HEAD~1:human_rating_sitemap.xml"]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            root = ET.fromstring(out)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            recovered = 0
            for url_elem in root.findall("sm:url", ns):
                loc_elem = url_elem.find("sm:loc", ns)
                lastmod_elem = url_elem.find("sm:lastmod", ns)
                if loc_elem is not None and loc_elem.text and lastmod_elem is not None and lastmod_elem.text:
                    loc = loc_elem.text.strip()
                    if loc not in existing:
                        existing[loc] = lastmod_elem.text.strip()
                        recovered += 1
            if recovered > 0:
                print(f"[*] Recovered {recovered} prior timestamps from git history (HEAD~1)")
        except Exception:
            pass

    return existing


def build_sitemap_xml(urls: list[str], output_path: str, existing_lastmods: dict[str, str]):
    """Build a sitemaps.org compliant XML sitemap preserving timestamps."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for url in urls:
        url_elem = ET.SubElement(root, "url")
        loc_elem = ET.SubElement(url_elem, "loc")
        loc_elem.text = url
        lastmod_elem = ET.SubElement(url_elem, "lastmod")
        lastmod_elem.text = existing_lastmods.get(url, today)

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with open(output_path, "wb") as f:
        f.write(xml_bytes)
        f.write(b"\n")
    print(f"[+] Written {len(urls)} URLs to {output_path}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sitemap_path = os.path.join(script_dir, "human_rating_sitemap.xml")
    pdf_sitemap_path = os.path.join(script_dir, "human_rating_pdf_sitemap.xml")
    imm_sitemap_path = os.path.join(script_dir, "imm_sitemap.xml")
    urls_txt_path = os.path.join(script_dir, "human_rating_urls.txt")

    existing_lastmods = load_existing_lastmods(sitemap_path)

    html_pages, pdf_docs = crawl_human_rating_portal()

    # 1. Full Consolidated Sitemap (HTML + PDFs)
    # Always ensure the main Human Rating Guidance landing page is index 0
    # so Onyx's web connector check_internet_connection(to_visit_list[0]) tests www.nasa.gov
    other_urls = sorted(set(html_pages + pdf_docs) - {START_URL})
    all_urls = [START_URL] + other_urls

    # SAFETY THRESHOLD CHECK
    if len(all_urls) < MINIMUM_EXPECTED_URLS:
        print(f"\n[!] FATAL ERROR: Discovered only {len(all_urls)} URLs (safety threshold is >= {MINIMUM_EXPECTED_URLS})!", file=sys.stderr)
        print(f"[!] Aborting to prevent accidental pruning of production sitemaps.", file=sys.stderr)
        sys.exit(1)

    # Partition documents
    tbs = [p for p in pdf_docs if any(k in p for k in ["ochmo-tb-", "ochmo-mtb-"])]
    hbs = [p for p in pdf_docs if any(k in p for k in ["hb-", "handbook", "design-processes"])]
    stds = [p for p in pdf_docs if any(k in p for k in ["std-", "standard", "m-qa-"])]
    imm_pdfs = [p for p in pdf_docs if any(k in p for k in ["cliff", "imm", "pra", "drm", "flexible_ultrasound"])]

    print("\n" + "=" * 70)
    print(" Document Collection Breakdown:")
    print("=" * 70)
    print(f"  Technical Briefs (TB/MTB):    {len(tbs)}")
    print(f"  Handbooks (HIDH, HIDP, HB):   {len(hbs)}")
    print(f"  Standards & Work Instructions:{len(stds)}")
    print(f"  IMM PDFs (CliFFs / DRMs / PR):{len(imm_pdfs)}")
    print(f"  Other Research & Reports:     {len(pdf_docs) - len(tbs) - len(hbs) - len(stds) - len(imm_pdfs)}")
    print(f"  HTML Guidance Pages:          {len(html_pages)}")
    print(f"  Total Indexed Items:          {len(all_urls)}")
    print("=" * 70)

    # 1. Full Consolidated Sitemap (HTML + PDFs)
    build_sitemap_xml(all_urls, sitemap_path, existing_lastmods)

    # 2. PDF Only Sitemap
    build_sitemap_xml(pdf_docs, pdf_sitemap_path, existing_lastmods)

    # 3. IMM Specific Subset Sitemap (for standalone connector option)
    imm_urls = sorted(set([u for u in html_pages if "imm" in u] + imm_pdfs))
    build_sitemap_xml(imm_urls, imm_sitemap_path, existing_lastmods)

    # 4. Text URL list
    with open(urls_txt_path, "w", encoding="utf-8") as f:
        for u in all_urls:
            f.write(f"{u}\n")
    print(f"[+] Written full URL list ({len(all_urls)} URLs) to {urls_txt_path}")


if __name__ == "__main__":
    main()
