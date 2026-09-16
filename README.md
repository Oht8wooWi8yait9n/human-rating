# NASA Human Rating Guidance & OCHMO Standards Sitemap

Automated web crawler and sitemap repository indexing NASA's **Human Rating Guidance** portal, Office of the Chief Health and Medical Officer (**OCHMO**) Technical Briefs, Standards, Handbooks, Reference Libraries, and the Integrated Medical Model (**IMM**).

- **Primary Entry Point**: [`https://www.nasa.gov/human-rating-guidance/`](https://www.nasa.gov/human-rating-guidance/)
- **Repository**: [`https://github.com/Oht8wooWi8yait9n/human-rating`](https://github.com/Oht8wooWi8yait9n/human-rating)

---

## What is Indexed

This repository replaces static spreadsheets and manual file uploads with a dynamic, self-updating crawler that maps the complete OCHMO Human Rating guidance architecture:

| Document Collection | Count | Key Documents & Series |
| :--- | :--- | :--- |
| **Technical Briefs (TB & MTB)** | **60 PDFs** | `OCHMO-TB-001` through `047`, `OCHMO-MTB-001` through `013`, and all current revision PDFs. |
| **NASA Handbooks** | **4 PDFs** | Human Integration Design Handbook (`NASA/SP-2010-3407/REV1`), Human Integration Design Processes (`NASA/TP-2014-218556`), Anthropometry & Biomechanics Handbook (`OCHMO-HB-004`). |
| **Standards & Work Instructions** | **19 PDFs** | `NASA-STD-3001` Vol 1 & 2 (with signatures & compliance matrices), Aviation Medical Certification Standards (`OCHMO-STD-1880.1`), Standards Revision Process Work Instruction (`M-QA-2021-025`). |
| **Integrated Medical Model (IMM)** | **333 PDFs** | All Clinical Finding Forms (CliFFs), DRM/PRA reports, clinical peer review documents, and runs across LEO, Lunar, and Mars. |
| **Operational & Clinical Libraries** | **96 PDFs** | Decompression Sickness (DCS) Prebreathe Reference Library, Vehicle Acceleration Limits Library, Flight Surgeon Mishap Investigation Handbook. |
| **HTML Guidance Pages** | **76 Pages** | In-depth topic overviews on habitability, environments, medical care, safety, and human-rating criteria. |
| **Total Indexed Resources** | **588 Items** | **512 Canonical PDFs + 76 HTML Pages** |

---

## Available Sitemaps & Feeds

All sitemaps conform to the standard [sitemaps.org 0.9 XML schema](http://www.sitemaps.org/schemas/sitemap/0.9).

1. **Full Consolidated Sitemap (PDFs + Guidance Pages)**:
   ```text
   https://raw.githubusercontent.com/Oht8wooWi8yait9n/human-rating/main/human_rating_sitemap.xml
   ```
   *(588 indexed URLs — Recommended for complete knowledge base coverage in Onyx)*

2. **PDF Documents Only**:
   ```text
   https://raw.githubusercontent.com/Oht8wooWi8yait9n/human-rating/main/human_rating_pdf_sitemap.xml
   ```
   *(512 direct PDF URLs — Ideal if you only wish to index official documents and reports)*

3. **IMM Subset Sitemap**:
   ```text
   https://raw.githubusercontent.com/Oht8wooWi8yait9n/human-rating/main/imm_sitemap.xml
   ```
   *(339 IMM-specific URLs — Available if you wish to configure a separate, scoped connector for IMM)*

4. **Plain Text URL List**:
   ```text
   https://raw.githubusercontent.com/Oht8wooWi8yait9n/human-rating/main/human_rating_urls.txt
   ```

---

## Onyx Web Connector Configuration

To index this entire collection into Onyx:

1. Navigate to **Onyx Admin** $\rightarrow$ **Connectors** $\rightarrow$ **Web**.
2. Click **Create Connector** and configure:
   - **Connector Name**: `NASA-Human-Rating-Guidance`
   - **Base URL**:
     ```text
     https://raw.githubusercontent.com/Oht8wooWi8yait9n/human-rating/main/human_rating_sitemap.xml
     ```
   - **Scrape Method**: Select **`sitemap`**
   - **Refresh Frequency**: `Weekly` (matches crawler schedule)
3. Save and trigger the initial crawl.

---

## Automated Weekly Updates

A GitHub Actions workflow ([`.github/workflows/update-sitemap.yml`](.github/workflows/update-sitemap.yml)) runs every **Sunday at 00:00 UTC** and can be triggered manually via `workflow_dispatch`.

It spiders `https://www.nasa.gov/human-rating-guidance/`, detects any new Technical Briefs, Handbook revisions, or reference papers, regenerates all sitemaps, and automatically commits updates with `github-actions[bot] [skip ci]`.
