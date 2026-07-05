# Repair Invalid PRM

Goal:

- rewrite malformed model output into strict ASPECT `.prm` syntax without
  changing the intended setup

Repair priorities:

1. restore valid `set ` lines
2. restore proper `subsection` / `end` nesting
3. remove prose, bullets, Markdown, JSON, and YAML
4. preserve intended geometry, physics, and parameter values
5. keep official names whenever known from docs or examples

Typical repair cases:

- parameter lines missing `set `
- subsection names emitted as headings
- bullet lists instead of config lines
- braces or JSON-like serialization
- partial truncation around nested subsections

Best repair inputs:

- broken `.prm` content
- syntax guide
- one matching official example
- ASPECT parser or runtime error message, if available

Important rule:

- if repair requires choosing between multiple plausible ASPECT names, prefer
  the one that matches official docs and examples for the target version
