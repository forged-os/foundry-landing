"""
Inject repo variables into index.html and write the result to _site/index.html.
Usage: python3 scripts/inject.py <DISCORD_INVITE> <FORGED_OS_URL>

Both placeholders appear inside double-quoted href attributes in index.html.
Values are HTML-escaped (html.escape quote=True) before injection, which is safe
in double-quoted attribute and text contexts.
"""
import html
import os
import re
import sys
import urllib.parse

if len(sys.argv) < 3:
    sys.exit("Usage: inject.py <DISCORD_INVITE> <FORGED_OS_URL>")

DISCORD_INVITE = sys.argv[1]
FORGED_OS_URL = sys.argv[2]

# Validate DISCORD_INVITE (defense-in-depth; bash pre-validates the same pattern).
if not re.fullmatch(r"[A-Za-z0-9_-]+", DISCORD_INVITE):
    sys.exit("Error: DISCORD_INVITE must match ^[A-Za-z0-9_-]+$")

# Allow only printable ASCII (0x21-0x7e). Rejects all control chars (C0, DEL,
# C1), non-ASCII, and whitespace in a single pass.
if not re.fullmatch(r'[\x21-\x7e]+', FORGED_OS_URL):
    sys.exit("Error: FORGED_OS_URL must contain only printable ASCII characters")
# Additionally reject characters that break out of a double-quoted HTML attribute.
# html.escape below handles the rest; this is defense-in-depth for the raw string.
if re.search(r'[<>"\'\\`]', FORGED_OS_URL):
    sys.exit("Error: FORGED_OS_URL contains characters unsafe for HTML injection")

parsed = urllib.parse.urlparse(FORGED_OS_URL)
if parsed.scheme != "https":
    sys.exit("Error: FORGED_OS_URL must use https")

# Validate hostname labels: each label must start/end with alphanumeric and
# contain only alphanumeric and hyphens. Empty labels (from leading/trailing/
# doubled dots) fail the regex — the `if label` guard is intentionally absent.
_label_re = re.compile(r"\A[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\Z")
hostname = parsed.hostname or ""
_h = hostname[:-1] if hostname.endswith(".") else hostname  # strip at most one trailing dot
if not _h or not all(_label_re.fullmatch(label) for label in _h.split(".")):
    sys.exit("Error: FORGED_OS_URL must have a valid hostname")

if parsed.username is not None or parsed.password is not None:
    sys.exit("Error: FORGED_OS_URL must not include userinfo")

with open("index.html", encoding="utf-8") as f:
    content = f.read()

for placeholder in ("YOUR_DISCORD_INVITE", "FORGED_OS_URL"):
    if placeholder not in content:
        sys.exit(f"Error: {placeholder} placeholder not found in index.html")

# HTML-escape values before injection (safe in double-quoted attribute and text contexts).
subs = {
    "YOUR_DISCORD_INVITE": html.escape("https://discord.gg/" + DISCORD_INVITE, quote=True),
    "FORGED_OS_URL": html.escape(FORGED_OS_URL, quote=True),
}
counts = {k: 0 for k in subs}

def replace(m):
    counts[m.group(0)] += 1
    return subs[m.group(0)]

# Longest-first alternation prevents prefix-match collisions.
pattern = re.compile("|".join(sorted(map(re.escape, subs), key=len, reverse=True)))
content = pattern.sub(replace, content)

# Defense-in-depth: verify substitution counts even though pre-checks guarantee presence.
missing = [k for k, v in counts.items() if v == 0]
if missing:
    sys.exit(f"Error: placeholders not substituted: {missing}")

os.makedirs("_site", exist_ok=True)
with open("_site/index.html", "w", encoding="utf-8") as f:
    f.write(content)
