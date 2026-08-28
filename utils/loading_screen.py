# utils/loading_screen.py
"""
Animated Loading Screen Component.
Shows the character-climbing-chart illustration with animated progress bar.
Uses st.components.v1.html to inject a full-page overlay that disappears automatically.
"""

import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components


def _get_image_b64(path: str) -> str:
    """Read an image file and return a base64 data URI."""
    p = Path(path)
    if not p.exists():
        return ""
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    suffix = p.suffix.lower().replace(".", "")
    mime = "png" if suffix == "png" else "jpeg"
    return f"data:image/{mime};base64,{b64}"


def show_loading_screen(message: str = "Analyzing Market Data", duration_ms: int = 2800):
    """
    Inject a full-page animated loading overlay that auto-hides after `duration_ms`.

    Args:
        message:     The headline message shown below the character.
        duration_ms: How many milliseconds to show the loading screen before fading out.
    """
    img_path = Path(__file__).parent.parent / "static" / "loading_screen.png"
    img_b64  = _get_image_b64(str(img_path))
    if not img_b64:
        # Fallback: just show a spinner if image missing
        return

    html_code = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: transparent;
    overflow: hidden;
  }}

  #loader-overlay {{
    position: fixed;
    inset: 0;
    z-index: 99999;
    background: radial-gradient(ellipse at center, #0d2818 0%, #051209 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    animation: fadeOut 0.6s ease-in-out {duration_ms}ms forwards;
  }}

  @keyframes fadeOut {{
    from {{ opacity: 1; visibility: visible; }}
    to   {{ opacity: 0; visibility: hidden; }}
  }}

  #loader-overlay.hidden {{
    display: none;
  }}

  .loader-image {{
    width: min(480px, 90vw);
    height: auto;
    animation: floatUp 2.2s ease-in-out infinite alternate;
    filter: drop-shadow(0 20px 60px rgba(34,197,94,0.35));
  }}

  @keyframes floatUp {{
    0%   {{ transform: translateY(0px);   }}
    100% {{ transform: translateY(-14px); }}
  }}

  .loader-text {{
    margin-top: 28px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 1.35rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-shadow: 0 0 30px rgba(34,197,94,0.5);
  }}

  .loader-sub {{
    margin-top: 8px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    color: #22c55e;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    animation: pulse 1.2s ease-in-out infinite;
  }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0.4; }}
  }}

  .progress-track {{
    margin-top: 20px;
    width: min(340px, 80vw);
    height: 8px;
    background: rgba(255,255,255,0.1);
    border-radius: 100px;
    overflow: hidden;
  }}

  .progress-bar {{
    height: 100%;
    background: linear-gradient(90deg, #16a34a 0%, #22c55e 50%, #4ade80 100%);
    border-radius: 100px;
    animation: loadProgress {duration_ms}ms cubic-bezier(0.1, 0.4, 0.8, 1.0) forwards;
    box-shadow: 0 0 12px rgba(34,197,94,0.7);
  }}

  @keyframes loadProgress {{
    0%   {{ width: 0%;   }}
    20%  {{ width: 18%;  }}
    45%  {{ width: 42%;  }}
    70%  {{ width: 68%;  }}
    90%  {{ width: 87%;  }}
    100% {{ width: 100%; }}
  }}
</style>
</head>
<body>
<div id="loader-overlay">
  <img class="loader-image" src="{img_b64}" alt="Loading" />
  <div class="loader-text">{message}</div>
  <div class="loader-sub">Loading...</div>
  <div class="progress-track">
    <div class="progress-bar"></div>
  </div>
</div>

<script>
  // After duration, remove from parent frame too
  setTimeout(function() {{
    var el = document.getElementById('loader-overlay');
    if (el) el.style.display = 'none';
  }}, {duration_ms + 700});
</script>
</body>
</html>
"""
    # Height 0 so the iframe takes no layout space; the overlay is position:fixed in the parent
    components.html(html_code, height=0, scrolling=False)
