"""Portable reports: no CDN, telemetry, source bodies, or external assets."""
from html import escape
import json


def label(value):
    # Render control characters visibly, including terminal escape sequences.
    return json.dumps(value, ensure_ascii=False)[1:-1].replace("\x1b", "\\u001b")


def render_text(result):
    lines = ["IMPACT TRAIL · explain the reach of a change", "",
             f"{len(result['changed'])} changed · {len(result['impacts'])} reached · {len(result['candidate_tests'])} candidate tests", ""]
    for item in result["impacts"]:
        lines.append(f"{'TEST' if item['kind'] == 'test' else 'FILE'}  {label(item['path'])}")
        if item["changed"]:
            lines.append("      directly changed")
        for edge in item["trail"]:
            lines.append(f"      {label(edge['dependency'])} → {label(edge['importer'])}:{edge['line']} [{edge['reason']}; {edge['snapshot']}]")
    if not result["impacts"]:
        lines.append("No reachable Python files found. This is not proof of no impact.")
    if result["warnings"]:
        lines += ["", "REVIEW NEEDED"] + ["- " + label(w) for w in result["warnings"]]
    lines += ["", *result["limitations"]]
    return "\n".join(lines)


def render_markdown(result):
    # Use HTML escaping inside code elements to handle hostile repository paths.
    code = lambda s: "<code>" + escape(label(s)) + "</code>"
    lines = ["## Impact Trail", "", f"**{len(result['changed'])} changed · {len(result['impacts'])} reached · {len(result['candidate_tests'])} candidate tests**", ""]
    for item in result["impacts"]:
        lines.append(f"- {code(item['path'])} — {item['kind']}" + ("; directly changed" if item["changed"] else ""))
        for edge in item["trail"]:
            lines.append(f"  - {code(edge['dependency'])} → {code(edge['importer'])}, line {edge['line']} ({edge['reason']}; {edge['snapshot']})")
    if result["warnings"]:
        lines += ["", "### Review needed", ""] + ["- " + escape(label(w)) for w in result["warnings"]]
    lines += ["", "### Limits", ""] + ["- " + x for x in result["limitations"]]
    return "\n".join(lines)


def render_html(result):
    e = lambda s: escape(label(s))
    cards = []
    for item in result["impacts"]:
        trail = "".join(
            f'<li><code>{e(edge["dependency"])}</code><span>imports into</span><code>{e(edge["importer"])}</code>'
            f'<small>line {edge["line"]} · {e(edge["reason"])} · {e(edge["snapshot"])}</small></li>'
            for edge in item["trail"])
        body = '<p class="direct">Directly changed in this comparison</p>' if item["changed"] else f'<ol>{trail}</ol>'
        cards.append(f'<article data-kind="{item["kind"]}"><header><span class="tag {item["kind"]}">{item["kind"]}</span>'
                     f'<h3>{e(item["path"])}</h3><span class="depth">{len(item["trail"])} hops</span></header>{body}</article>')
    if not cards:
        cards.append('<article><h3>No reachable Python files found</h3><p>This does not prove that the change has no impact.</p></article>')
    warnings = "".join(f"<li>{e(x)}</li>" for x in result["warnings"])
    limits = "".join(f"<li>{escape(x)}</li>" for x in result["limitations"])
    stats = "".join(f'<div><strong>{value}</strong><span>{name}</span></div>' for value, name in [
        (len(result["changed"]), "Changed paths"), (len(result["impacts"]), "Reached files"),
        (len(result["candidate_tests"]), "Candidate tests"), (result["files_analyzed"], "Files analyzed")])
    changed = "".join(f'<code>{e(x)}</code>' for x in result["changed"]) or "No changes detected"
    baseline = escape(result["baseline"][:12]) if result["baseline"] else "Explicit paths"
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Impact Trail · Change report</title><style>
:root{color-scheme:dark;--bg:#10131d;--panel:#191e2c;--ink:#eef0f7;--muted:#a7b0c7;--line:#30384d;--accent:#b8a3ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 system-ui,sans-serif}main{max-width:1060px;margin:auto;padding:48px 28px}nav{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:13px}.brand{font-weight:800;letter-spacing:2px;color:var(--accent)}h1{font-size:clamp(38px,6vw,64px);letter-spacing:-2px;line-height:1.1;margin:42px 0 18px}h2{font-size:22px;margin-top:38px}h3{font-size:15px;margin:0;overflow-wrap:anywhere}p{color:var(--muted);max-width:720px}.eyebrow{color:var(--accent);font-size:12px;text-transform:uppercase;letter-spacing:2px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:32px 0}.stats div{background:var(--panel);padding:20px;border:1px solid var(--line);border-radius:14px}.stats strong{display:block;font-size:36px;line-height:1.3}.stats span{font-size:13px;color:var(--muted)}.changed{display:flex;gap:10px;flex-wrap:wrap}code{font:13px/1.7 ui-monospace,monospace;overflow-wrap:anywhere}.changed code{padding:6px 12px;border:1px solid var(--line);border-radius:8px}article{background:var(--panel);border:1px solid var(--line);border-radius:12px;margin:12px 0;padding:22px}article header{display:flex;gap:12px;align-items:center}.tag{font-size:11px;text-transform:uppercase;background:#35304f;color:#d5c5ff;padding:3px 8px;border-radius:5px}.tag.test{background:#193f39;color:#9de2ca}.depth{margin-left:auto;white-space:nowrap;color:var(--muted);font-size:12px}ol{list-style:none;padding:0 0 0 14px;border-left:2px solid #6d5c9e;margin:20px 0 0 8px}ol li{margin:14px 0;display:flex;gap:8px;flex-wrap:wrap}ol span,small{color:var(--muted);font-size:12px}small{flex-basis:100%}.direct{font-size:13px;margin:12px 0 0}.controls{display:flex;gap:10px;flex-wrap:wrap}input,select{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px}input{flex:1;min-width:180px}.notice{border:1px solid #675538;background:#292417;border-radius:12px;padding:18px 24px;margin:24px 0}.notice h2{margin:0;font-size:17px}.notice li{color:#e7d6ae}footer{border-top:1px solid var(--line);margin-top:40px;padding-top:20px;color:var(--muted);font-size:13px}footer li{margin:8px 0}label{font-size:13px;color:var(--muted)}[hidden]{display:none!important}@media(max-width:650px){main{padding:25px 18px}.stats{grid-template-columns:repeat(2,1fr)}article header{flex-wrap:wrap}.depth{margin-left:0}nav{flex-wrap:wrap}}@media print{body{background:white;color:black}.controls{display:none}article,.stats div{break-inside:avoid;background:white;color:black}p,footer,small,ol span{color:#444}}
</style></head><body><main>
<nav><span class="brand">◈ IMPACT TRAIL</span><span>LOCAL ANALYSIS · NO CODE EXECUTED</span></nav>
<p class="eyebrow">A change is only the beginning</p><h1>Follow the impact.</h1>
<p>See where a Python change may travel. Every result comes with an import trail you can inspect — before you open a pull request.</p>
''' + f'<section class="stats" aria-label="Summary">{stats}</section><h2>Starting points</h2><p>Baseline: {baseline}</p><div class="changed">{changed}</div>' + (
        f'<aside class="notice"><h2>Review needed · run the full suite</h2><ul>{warnings}</ul></aside>' if warnings else '') + '''
<h2>Evidence trails</h2><div class="controls"><input id="search" type="search" aria-label="Filter files" placeholder="Filter by file path…"><select id="kind" aria-label="File type"><option value="all">All files</option><option value="test">Tests only</option><option value="module">Modules only</option></select></div>
''' + f'<section id="trails">{"".join(cards)}</section><p id="empty" hidden>No matching files.</p><footer><strong>Evidence, not a safety verdict.</strong><ul>{limits}</ul><p>Generated by Impact Trail 0.1.0 · Report contains file paths and import locations, not source bodies. Review paths before sharing.</p></footer>' + '''
</main><script>
const search=document.getElementById('search'),kind=document.getElementById('kind');
function filter(){let visible=0;document.querySelectorAll('article').forEach(card=>{const match=card.textContent.toLowerCase().includes(search.value.toLowerCase())&&(kind.value==='all'||card.dataset.kind===kind.value);card.hidden=!match;if(match)visible++;});document.getElementById('empty').hidden=visible!==0;}
search.addEventListener('input',filter);kind.addEventListener('change',filter);
</script></body></html>'''
