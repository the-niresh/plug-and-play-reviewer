"""One styled shell for the HTML the control plane serves to a browser.

These pages are the only part of the hosted service a person looks at outside the
dashboard, and they show up in the middle of signing in. Unstyled black-on-white with a
default button reads as a crash, not as a step in a flow, so someone halfway through
pairing a terminal reasonably concludes the product is broken.

The CSS is inline and tiny on purpose. This service serves no static assets, must render
before anything else loads, and has to work under a strict CSP with no external
stylesheet. Colours are the site's own tokens (apps/web/src/app/globals.css), including
the dark set, so the page matches whichever theme the reader's system is set to.
"""

from __future__ import annotations

import html

_STYLE = """
:root{
  --bg:#fafaf7; --fg:#111111; --card:#ffffff; --muted:#5c5c5c; --border:#e5e5e5;
  --accent:#111111; --accent-fg:#fafaf7;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0a0a0a; --fg:#fafafa; --card:#111111; --muted:#a3a3a3; --border:#262626;
    --accent:#fafafa; --accent-fg:#0a0a0a;
  }
}
*{box-sizing:border-box}
body{
  margin:0; padding:2rem 1.25rem; min-height:100vh;
  display:flex; align-items:flex-start; justify-content:center;
  background:var(--bg); color:var(--fg);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}
main{
  width:100%; max-width:32rem; margin-top:12vh;
  background:var(--card); border:1px solid var(--border); border-radius:12px;
  padding:2rem 1.75rem;
}
.mark{
  display:flex; align-items:center; gap:.6rem;
  font-size:.75rem; letter-spacing:.08em; text-transform:uppercase;
  color:var(--muted); margin:0 0 1.25rem;
}
.mark svg{width:1.5rem;height:1.5rem;flex:none}
h1{font-size:1.35rem; line-height:1.3; margin:0 0 .75rem; letter-spacing:-.01em}
p{margin:0 0 1rem; color:var(--muted)}
p.lead{color:var(--fg)}
strong{color:var(--fg)}
form{margin:1.5rem 0 1rem}
button{
  font:inherit; font-weight:600; font-size:.95rem; cursor:pointer;
  background:var(--accent); color:var(--accent-fg);
  border:0; border-radius:8px; padding:.65rem 1.15rem;
}
button:hover{opacity:.9}
button:focus-visible,a:focus-visible{outline:2px solid var(--accent); outline-offset:3px}
a{color:var(--fg); text-underline-offset:3px}
.quiet{font-size:.9rem}
code{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.85em;
  background:var(--bg); border:1px solid var(--border); border-radius:5px; padding:.1rem .35rem;
}
"""

# The product mark, reduced to what still reads at 24px: the lens, the bug inside it, and
# the git branch it sits on. It is currentColor throughout so it works in both themes.
_MARK = (
    '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.6" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M4 44V10"/><path d="M4 26c0-3.5 2.5-5.5 5.5-5.5"/>'
    '<circle cx="24" cy="21" r="12.5"/><path d="M33.5 30.5L41 38" stroke-width="3.6"/>'
    '<ellipse cx="24" cy="23" rx="4.4" ry="5.2"/><circle cx="24" cy="16.4" r="2.1" '
    'fill="currentColor"/><path d="M24 18.4v9.6"/>'
    "</svg>"
)


def render_page(*, title: str, heading: str, body: str, head: str = "") -> str:
    """`title` and `heading` are escaped here. `body` is trusted markup the caller built,
    so every value interpolated into it must already be escaped by the caller."""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title>"
        f"{head}"
        f"<style>{_STYLE}</style></head>\n"
        "<body><main>\n"
        f'<p class="mark">{_MARK}<span>Plug and Play Reviewer</span></p>\n'
        f"<h1>{html.escape(heading)}</h1>\n"
        f"{body}\n"
        "</main></body></html>"
    )
