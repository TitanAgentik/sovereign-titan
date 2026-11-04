#!/usr/bin/env python3
"""Exports `docs/SOVEREIGN_TITAN_15_PAGE_MASTER_WHITEPAPER.md` and
`docs/SOVEREIGN_TITAN_20_PAGE_DEFINITIVE_SYSTEM_BIBLE.md` to publication-grade
multi-page PDF and standalone HTML books using headless Chromium.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path("/home/titanagentik/sovereign-titan")
ARTIFACT_DIR = Path(
    "/home/titanagentik/.gemini/antigravity/brain/c882eef8-a106-4d00-badc-7f1862d299b2"
)
MD_SOURCE = WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_15_PAGE_MASTER_WHITEPAPER.md"
HTML_OUT = WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_15_PAGE_MASTER_WHITEPAPER.html"
PDF_WORKSPACE_OUT = (
    WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_15_PAGE_MASTER_WHITEPAPER.pdf"
)
PDF_ARTIFACT_OUT = ARTIFACT_DIR / "SOVEREIGN_TITAN_15_PAGE_MASTER_WHITEPAPER.pdf"

BIBLE_20_MD_SOURCE = (
    WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_20_PAGE_DEFINITIVE_SYSTEM_BIBLE.md"
)
BIBLE_20_HTML_OUT = (
    WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_20_PAGE_DEFINITIVE_SYSTEM_BIBLE.html"
)
BIBLE_20_PDF_WORKSPACE_OUT = (
    WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_20_PAGE_DEFINITIVE_SYSTEM_BIBLE.pdf"
)
BIBLE_20_PDF_ARTIFACT_OUT = (
    ARTIFACT_DIR / "SOVEREIGN_TITAN_20_PAGE_DEFINITIVE_SYSTEM_BIBLE.pdf"
)
BIBLE_20_MD_ARTIFACT_OUT = (
    ARTIFACT_DIR / "sovereign_titan_20_page_definitive_system_bible.md"
)


def _format_latex_inline(expr: str) -> str:
    """Converts LaTeX math expressions into clean HTML/Unicode math markup for offline PDF rendering."""
    s = expr.strip()
    replacements = [
        (r"\\ge\b", "≥"),
        (r"\\le\b", "≤"),
        (r"\\neq\b", "≠"),
        (r"\\ll\b", "≪"),
        (r"\\gg\b", "≫"),
        (r"\\equiv\b", "≡"),
        (r"\\approx\b", "≈"),
        (r"\\implies\b", "⟹"),
        (r"\\iff\b", "⟺"),
        (r"\\in\b", "∈"),
        (r"\\times\b", "×"),
        (r"\\cdot\b", "·"),
        (r"\\to\b", "→"),
        (r"\\rightarrow\b", "→"),
        (r"\\longrightarrow\b", "⟶"),
        (r"\\leftrightarrow\b", "↔"),
        (r"\\xrightarrow\{([^}]+)\}", r"→<sub>\1</sub>"),
        (r"\\parallel\b", "∥"),
        (r"\\dots\b", "…"),
        (r"\\sum_\{([^}]+)\}\^\{([^}]+)\}", r"∑<sub>\1</sub><sup>\2</sup>"),
        (r"\\sum_\{([^}]+)\}", r"∑<sub>\1</sub>"),
        (r"\\max_\{([^}]+)\}", r"max<sub>\1</sub>"),
        (r"\\min_\{([^}]+)\}", r"min<sub>\1</sub>"),
        (r"\\arg\\min_([a-zA-Z0-9]+)", r"argmin<sub>\1</sub>"),
        (r"\\arg\\max_([a-zA-Z0-9]+)", r"argmax<sub>\1</sub>"),
        (r"\\Phi\b", "Φ"),
        (r"\\Pi\b", "Π"),
        (r"\\Delta\b", "Δ"),
        (r"\\delta\b", "δ"),
        (r"\\gamma\b", "γ"),
        (r"\\lambda\b", "λ"),
        (r"\\mu\b", "μ"),
        (r"\\nu\b", "ν"),
        (r"\\phi\b", "φ"),
        (r"\\sigma\b", "σ"),
        (r"\\tau\b", "τ"),
        (r"\\partial\b", "∂"),
        (r"\\mid\b", "|"),
        (r"\\mathcal\{E\}", "ℰ"),
        (r"\\mathcal\{L\}", "ℒ"),
        (r"\\mathcal\{B\}", "ℬ"),
        (r"\\text\{([^}]+)\}", r"\1"),
        (r"\\texttt\{([^}]+)\}", r"<code>\1</code>"),
        (r"\\bar\{([^}]+)\}", r"\1̄"),
        (r"\\ln\b", "ln"),
        (r"\\log\b", "log"),
        (r"\\exp\b", "exp"),
        (r"\\max\b", "max"),
        (r"\\min\b", "min"),
        (r"\\Big\[", "["),
        (r"\\Big\]", "]"),
        (r"\\big\(", "("),
        (r"\\big\)", ")"),
        (r"\\left\\lfloor", "⌊"),
        (r"\\right\\rfloor", "⌋"),
        (r"\\lfloor", "⌊"),
        (r"\\rfloor", "⌋"),
        (r"\\left\(", "("),
        (r"\\right\)", ")"),
        (r"\\left\[", "["),
        (r"\\right\]", "]"),
        (r"\\left\\\{", "{"),
        (r"\\right\\\}", "}"),
        (r"\\left\|", "|"),
        (r"\\right\|", "|"),
        (r"\\begin\{cases\}", "{ "),
        (r"\\end\{cases\}", " }"),
        (r"\\\\", " ; "),
        (r"&", " "),
        (r"\\pmod\{([^}]+)\}", r"(mod \1)"),
        (r"\\bmod\b", "mod"),
        (r"\\sqrt\{([^}]+)\}", r"√(\1)"),
        (r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1) / (\2)"),
        (r"_\{([^}]+)\}", r"<sub>\1</sub>"),
        (r"\^\{([^}]+)\}", r"<sup>\1</sup>"),
        (r"_([a-zA-Z0-9]+)", r"<sub>\1</sub>"),
        (r"\^([a-zA-Z0-9\*]+)", r"<sup>\1</sup>"),
        (r"\\\{", "{"),
        (r"\\\}", "}"),
        (r"\\%", "%"),
        (r"\\\$", "$"),
        (r"\\,", " "),
        (r"\\qquad\b", " &nbsp;&nbsp;&nbsp;&nbsp; "),
        (r"\\quad\b", " &nbsp;&nbsp; "),
    ]
    for pat, rep in replacements:
        s = re.sub(pat, rep, s)
    return f'<span class="math-expr">{s}</span>'


def _format_inline(text: str) -> str:
    """Formats inline markdown (code spans, links, bold, italics, inline math)."""
    code_spans: list[str] = []

    def _save_code(m: re.Match[str]) -> str:
        idx = len(code_spans)
        code_spans.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"@@CODESPAN_{idx}@@"

    text = re.sub(r"`([^`]+)`", _save_code, text)

    # Links [label](url)
    def _replace_link(m: re.Match[str]) -> str:
        label = m.group(1)
        url = html.escape(m.group(2))
        return f'<a href="{url}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _replace_link, text)

    # Escaped dollars \$
    text = text.replace(r"\$", "&#36;")

    # Inline math $...$
    text = re.sub(
        r"\$([^$\n]+)\$",
        lambda m: _format_latex_inline(m.group(1)),
        text,
    )

    # Bold & Italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)

    for idx, span in enumerate(code_spans):
        text = text.replace(f"@@CODESPAN_{idx}@@", span)

    return text


def _render_mermaid_diagram(code: str) -> str:
    """Renders Mermaid diagram blocks as styled institutional architecture boxes."""
    if "Layer 1: Sub-Slot Ingestion" in code:
        return """
        <div class="arch-diagram">
          <div class="arch-stage">
            <div class="arch-title">LAYER 1 · SUB-SLOT INGESTION (&lt;0.4ms)</div>
            <div class="arch-grid">
              <div class="arch-node">Helius Yellowstone gRPC + Jito ShredStream + preconfSubscribe</div>
              <div class="arch-node">Local jupiter-swap-api (:8080 · 0.4ms) + 2,000-Pool RAMDisk Mirror</div>
              <div class="arch-node">SocialData WSS + Telegram MTProto + Binance WSS + Pyth Lazer 1ms</div>
            </div>
          </div>
          <div class="arch-arrow">▼</div>
          <div class="arch-stage">
            <div class="arch-title">LAYER 2 · 6-LAYER FORENSICS &amp; BAYESIAN GATE (&lt;2.5ms)</div>
            <div class="arch-grid">
              <div class="arch-node">Louvain Shadow Cluster + Tarjan O(V+E) SCC Wash Filter</div>
              <div class="arch-node">MELT 122-Feature Gate + 5m Rug_t Kill-Switch (MCC 0.874)</div>
              <div class="arch-node">Bayesian Confluence Gate: P(Win | ℰ) ≥ 92.5% + Iron Dome (VPIN ≤ 0.78)</div>
            </div>
          </div>
          <div class="arch-arrow">▼</div>
          <div class="arch-stage">
            <div class="arch-title">LAYER 3 · 11-ENGINE EXECUTION &amp; 3 ZERO-LOSS LOCKS (&lt;1.2ms)</div>
            <div class="arch-grid">
              <div class="arch-node">4-Protocol Mega-Flash Syndicate ($100K → $1M → $10M → $50M+ · 0 SOL Risk)</div>
              <div class="arch-node">Whole-Solana Alpha: Pyth Lazer, CLMM Liquidations, JLP Basis &amp; 20-LST Triangles</div>
              <div class="arch-node">25-Shard Late-Curve (65%–78%), 84.5 SOL Migration &amp; 3.5s Velocity Scratch</div>
              <div class="arch-node">On-Chain profit_guard Rust CPI + Native Jupiter Guard + +0.85% BE Floor Ratchet</div>
            </div>
          </div>
          <div class="arch-arrow">▼</div>
          <div class="arch-stage highlight">
            <div class="arch-title">LAYER 4 · UNCAPPED AUTO-COMPOUNDING &amp; 4-ECHELON STRATEGY EVOLUTION</div>
            <div class="arch-grid">
              <div class="arch-node">100% Profit Auto-Reinvest: 50% DLMM/Funding · 30% Vault · 20% 25-Shard Waves</div>
              <div class="arch-node">Echelon 1 ($5k–$12k/d) → Echelon 2 ($15k–$35k/d) → Echelon 3 ($40k–$95k/d) → Echelon 4 ($100k+/d+ Uncapped)</div>
            </div>
          </div>
        </div>
        """
    return """
    <div class="arch-diagram">
      <div class="arch-stage">
        <div class="arch-title">GOLDEN 5 PHASED ROLLOUT STATE MACHINE (0.00 SOL PRINCIPAL RISK)</div>
        <div class="arch-grid">
          <div class="arch-node"><strong>STEP 1 (Boot):</strong> Zero-Risk Flash, Sanctum LST Depeg, 5-Tx Knapsack, DLMM &amp; Funding (0.00 SOL Risk)</div>
          <div class="arch-node"><strong>STEP 2 (≥ 8 SOL Profit):</strong> 25-Shard Late-Curve Squeeze (65%–78%) &amp; 84.5 SOL Migration (House Profit Only)</div>
          <div class="arch-node"><strong>STEP 3 (≥ 20 SOL Profit):</strong> Home-Run Hunters (Bridge Lookahead + :8002 GPU Vision + Polymarket)</div>
          <div class="arch-node"><strong>STEP 4 (≥ 100 SOL Profit):</strong> Sovereign Endowment + 4-Echelon Uncapped Scaling (&gt;30% DD Auto Step-Down to Step 1)</div>
        </div>
      </div>
    </div>
    """


def convert_markdown_to_html(
    md_text: str,
    compact: bool = False,
    page_break_on_page_headings: bool = False,
) -> str:
    """Converts Markdown into print-ready HTML."""
    lines = md_text.splitlines()
    out: list[str] = []
    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []
    in_ul = False
    in_ol = False
    page_counter = 0

    def _close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def _close_table() -> None:
        nonlocal in_table, table_rows
        if not in_table:
            return
        if table_rows:
            tbl_cls = "data-table dense-table" if len(table_rows) >= 15 else "data-table"
            out.append(f'<table class="{tbl_cls}">')
            header = table_rows[0]
            out.append("<thead><tr>")
            for cell in header:
                out.append(f"<th>{_format_inline(cell.strip())}</th>")
            out.append("</tr></thead><tbody>")
            for row in table_rows[1:]:
                if all(set(c.strip()) <= {"-", ":", " "} for c in row):
                    continue
                out.append("<tr>")
                for cell in row:
                    out.append(f"<td>{_format_inline(cell.strip())}</td>")
                out.append("</tr>")
            out.append("</tbody></table>")
        in_table = False
        table_rows = []

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()

        # Code block handling
        if stripped.startswith("```"):
            _close_lists()
            _close_table()
            if not in_code_block:
                in_code_block = True
                code_lang = stripped[3:].strip()
                code_lines = []
            else:
                in_code_block = False
                code_body = "\n".join(code_lines)
                if code_lang == "mermaid":
                    out.append(_render_mermaid_diagram(code_body))
                else:
                    out.append(
                        f'<pre class="code-block"><code>{html.escape(code_body)}</code></pre>'
                    )
            i += 1
            continue

        if in_code_block:
            code_lines.append(raw_line)
            i += 1
            continue

        # Display math $$...$$
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            _close_lists()
            _close_table()
            expr = stripped[2:-2]
            out.append(f'<div class="math-block">{_format_latex_inline(expr)}</div>')
            i += 1
            continue

        # Table rows
        if stripped.startswith("|") and stripped.endswith("|"):
            _close_lists()
            in_table = True
            cells = [c for c in stripped[1:-1].split("|")]
            table_rows.append(cells)
            i += 1
            continue
        else:
            _close_table()

        if not stripped:
            _close_lists()
            i += 1
            continue

        if stripped == "---":
            _close_lists()
            if not page_break_on_page_headings:
                out.append('<hr class="section-divider" />')
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            _close_lists()
            out.append(f'<h1 class="doc-title">{_format_inline(stripped[2:])}</h1>')
        elif stripped.startswith("## "):
            _close_lists()
            heading_text = stripped[3:]
            if heading_text.startswith("PAGE "):
                page_counter += 1
                pb_class = (
                    "page-section page-break-before"
                    if (page_break_on_page_headings and page_counter > 1)
                    else "page-section"
                )
                out.append(
                    f'<div class="{pb_class}"><h2 class="page-heading">{_format_inline(heading_text)}</h2></div>'
                )
            else:
                out.append(f'<h2 class="section-heading">{_format_inline(heading_text)}</h2>')
        elif stripped.startswith("### "):
            _close_lists()
            out.append(f'<h3 class="sub-heading">{_format_inline(stripped[4:])}</h3>')
        elif re.match(r"^\d+\.\s+", stripped):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            item_body = re.sub(r"^\d+\.\s+", "", stripped)
            out.append(f"<li>{_format_inline(item_body)}</li>")
        elif stripped.startswith("- "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_format_inline(stripped[2:])}</li>")
        else:
            _close_lists()
            out.append(f"<p>{_format_inline(stripped)}</p>")

        i += 1

    _close_lists()
    _close_table()

    body_html = "\n".join(out)
    if page_break_on_page_headings:
        body_font = "7.55pt"
        body_lh = "1.24"
        page_margin = "7.5mm 9mm 7.5mm 9mm"
        table_font = "6.8pt"
        table_pad = "2.2px 4px"
        code_font = "6.8pt"
    else:
        body_font = "8.1pt" if compact else "9.8pt"
        body_lh = "1.28" if compact else "1.46"
        page_margin = "8.5mm 10mm 9mm 10mm" if compact else "12mm 13mm 13mm 13mm"
        table_font = "7.4pt" if compact else "8.1pt"
        table_pad = "3px 5px" if compact else "4px 6px"
        code_font = "7.4pt" if compact else "8pt"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Sovereign Titan v2.0 — Institutional Technical &amp; Operational Manual</title>
<style>
  @page {{
    size: letter;
    margin: {page_margin};
  }}
  * {{
    box-sizing: border-box;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: {body_font};
    line-height: {body_lh};
    color: #0f172a;
    background: #ffffff;
    margin: 0;
    padding: 0;
  }}
  .doc-banner {{
    background: linear-gradient(135deg, #061814 0%, #0b192c 60%, #170f2e 100%);
    color: #f8fafc;
    padding: 9px 13px;
    border-radius: 6px;
    border-left: 5px solid #10b981;
    margin-bottom: 6px;
  }}
  .doc-banner .subtitle {{
    color: #34d399;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 8.0pt;
    font-weight: 700;
    letter-spacing: 0.4px;
    text-transform: uppercase;
  }}
  h1.doc-title {{
    font-size: 12.5pt;
    font-weight: 800;
    color: #064e3b;
    margin: 2px 0 5px 0;
    padding-bottom: 3px;
    border-bottom: 2px solid #10b981;
    letter-spacing: -0.2px;
  }}
  .page-section {{
    margin-top: 6px;
    page-break-inside: avoid;
  }}
  .page-break-before {{
    page-break-before: always;
    break-before: page;
    margin-top: 0;
  }}
  h2.page-heading {{
    font-size: 10.2pt;
    font-weight: 800;
    color: #ffffff;
    background: linear-gradient(90deg, #064e3b 0%, #0f172a 100%);
    padding: 4.5px 9px;
    border-radius: 4px;
    border-left: 4px solid #10b981;
    margin: 4px 0 5px 0;
    letter-spacing: 0.15px;
    page-break-after: avoid;
  }}
  h2.section-heading {{
    font-size: 9.8pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 1.5px solid #cbd5e1;
    padding-bottom: 2px;
    margin: 5px 0 4px 0;
    page-break-after: avoid;
  }}
  h3.sub-heading {{
    font-size: 8.6pt;
    font-weight: 700;
    color: #0369a1;
    margin: 5px 0 2.5px 0;
    page-break-after: avoid;
  }}
  p {{
    margin: 2.5px 0 4px 0;
    text-align: justify;
  }}
  ul, ol {{
    margin: 2.5px 0 4px 0;
    padding-left: 15px;
  }}
  li {{
    margin-bottom: 2px;
  }}
  code {{
    font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
    font-size: {code_font};
    background: #f1f5f9;
    color: #0f172a;
    padding: 0.5px 2.5px;
    border-radius: 3px;
    border: 1px solid #e2e8f0;
  }}
  a {{
    color: #0284c7;
    text-decoration: none;
  }}
  pre.code-block {{
    font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
    font-size: {code_font};
    background: #0f172a;
    color: #e2e8f0;
    padding: 5px 7px;
    border-radius: 5px;
    border-left: 3.5px solid #10b981;
    overflow-x: auto;
    margin: 3.5px 0;
  }}
  pre.code-block code {{
    background: transparent;
    color: inherit;
    border: none;
    padding: 0;
  }}
  table.data-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 3.5px 0 5px 0;
    font-size: {table_font};
  }}
  table.data-table th {{
    background: #0f172a;
    color: #f8fafc;
    font-weight: 700;
    text-align: left;
    padding: {table_pad};
    border: 1px solid #334155;
  }}
  table.data-table td {{
    padding: {table_pad};
    border: 1px solid #cbd5e1;
    vertical-align: top;
  }}
  table.data-table tr:nth-child(even) td {{
    background: #f8fafc;
  }}
  table.dense-table {{
    font-size: 5.5pt;
    line-height: 1.08;
    margin: 2px 0;
  }}
  table.dense-table th, table.dense-table td {{
    padding: 1.1px 2.5px;
  }}
  table.dense-table code {{
    font-size: 5.4pt;
    padding: 0 1.5px;
    border: none;
  }}
  .math-block {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 3.5px solid #0284c7;
    border-radius: 4px;
    padding: 4.5px 8px;
    margin: 4px 0;
    text-align: center;
    font-family: "Cambria Math", "STIX Two Math", Georgia, serif;
    font-size: 8.6pt;
  }}
  .math-expr {{
    font-family: "Cambria Math", "STIX Two Math", Georgia, serif;
    font-weight: 600;
    color: #0f172a;
  }}
  hr.section-divider {{
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 6px 0;
  }}
  .arch-diagram {{
    background: #f8fafc;
    border: 1.5px solid #94a3b8;
    border-radius: 6px;
    padding: 6px 8px;
    margin: 4px 0 6px 0;
  }}
  .arch-stage {{
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #0284c7;
    border-radius: 4px;
    padding: 4px 7px;
  }}
  .arch-stage.highlight {{
    border-left-color: #10b981;
    background: #ecfdf5;
  }}
  .arch-title {{
    font-size: 7.8pt;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 3px;
  }}
  .arch-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 3.5px;
  }}
  .arch-node {{
    font-size: 7.4pt;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 2.5px 5px;
  }}
  .arch-arrow {{
    text-align: center;
    font-size: 8pt;
    color: #0284c7;
    line-height: 1.05;
    margin: 1.5px 0;
  }}
</style>
</head>
<body>
<div class="doc-banner">
  <div class="subtitle">SOVEREIGN TITAN OS v2.0 · INSTITUTIONAL TECHNICAL &amp; OPERATIONAL SYSTEM BIBLE</div>
  <div style="font-size: 8.0pt; color: #cbd5e1; margin-top: 2px;">
    96-Core Threadripper PRO 9995WX · Dual RTX PRO 6000 Blackwell (192GB GDDR7) · 128GB DDR5 RAMDisk · 32 Agents / 96 Subagents · $100K–$50M Mega-Flash Syndicate
  </div>
</div>
{body_html}
</body>
</html>
"""


def export_markdown_document(
    md_source: Path,
    html_out: Path,
    pdf_targets: list[Path],
    compact: bool = False,
    page_break_on_page_headings: bool = False,
) -> None:
    md_text = md_source.read_text(encoding="utf-8")
    html_content = convert_markdown_to_html(
        md_text,
        compact=compact,
        page_break_on_page_headings=page_break_on_page_headings,
    )
    html_out.write_text(html_content, encoding="utf-8")

    for pdf_target in pdf_targets:
        pdf_target.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "/usr/bin/chromium",
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_target}",
            f"file://{html_out}",
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[OK] Exported PDF: {pdf_target} ({pdf_target.stat().st_size:,} bytes)")


def main() -> None:
    export_markdown_document(
        md_source=MD_SOURCE,
        html_out=HTML_OUT,
        pdf_targets=[PDF_WORKSPACE_OUT, PDF_ARTIFACT_OUT],
    )
    runbook_md = WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_LIVE_CAPITAL_24X7_RUNBOOK.md"
    if runbook_md.exists():
        export_markdown_document(
            md_source=runbook_md,
            html_out=WORKSPACE_ROOT
            / "docs"
            / "SOVEREIGN_TITAN_LIVE_CAPITAL_24X7_RUNBOOK.html",
            pdf_targets=[
                WORKSPACE_ROOT
                / "docs"
                / "SOVEREIGN_TITAN_LIVE_CAPITAL_24X7_RUNBOOK.pdf",
                ARTIFACT_DIR / "SOVEREIGN_TITAN_LIVE_CAPITAL_24X7_RUNBOOK.pdf",
            ],
        )

    operator_md = WORKSPACE_ROOT / "docs" / "SOVEREIGN_TITAN_OPERATOR_ACTION_MANUAL.md"
    if operator_md.exists():
        export_markdown_document(
            md_source=operator_md,
            html_out=WORKSPACE_ROOT
            / "docs"
            / "SOVEREIGN_TITAN_OPERATOR_ACTION_MANUAL.html",
            pdf_targets=[
                WORKSPACE_ROOT
                / "docs"
                / "SOVEREIGN_TITAN_OPERATOR_ACTION_MANUAL.pdf",
                ARTIFACT_DIR / "SOVEREIGN_TITAN_OPERATOR_ACTION_MANUAL.pdf",
            ],
            compact=True,
        )

    if BIBLE_20_MD_SOURCE.exists():
        BIBLE_20_MD_ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BIBLE_20_MD_SOURCE, BIBLE_20_MD_ARTIFACT_OUT)
        print(
            f"[OK] Copied Markdown: {BIBLE_20_MD_ARTIFACT_OUT} ({BIBLE_20_MD_ARTIFACT_OUT.stat().st_size:,} bytes)"
        )
        export_markdown_document(
            md_source=BIBLE_20_MD_SOURCE,
            html_out=BIBLE_20_HTML_OUT,
            pdf_targets=[BIBLE_20_PDF_WORKSPACE_OUT, BIBLE_20_PDF_ARTIFACT_OUT],
            compact=True,
            page_break_on_page_headings=True,
        )


if __name__ == "__main__":
    main()
