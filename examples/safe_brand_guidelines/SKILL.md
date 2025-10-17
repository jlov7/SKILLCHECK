---
name: "Brand Voice Editor (Safe Demo)"
description: "Edits copy to match the included brand-voice guide; never fetches external data or executes code."
version: "1.0.0"
---

# What this Skill does
Help rewrite short passages so they conform to the **brand voice** in `style-guide/brand-voice.md`.  
It is **read-only** and **offline**: no network calls, no external tools, no code execution.

## Files
- `style-guide/brand-voice.md` — the sole reference document for tone, vocabulary, and formatting.

## How Claude should use this Skill
1. Read `style-guide/brand-voice.md`.  
2. For each input passage, return a short analysis (what to change) and a revised version that follows the guide.  
3. Never invent policies beyond the file; if conflict, defer to the file.

## Constraints
- **No external sources.** Do not browse or fetch network content.
- **No writes.** Do not create or modify files.
- **No code execution.** Treat this as documentation-only.

## Examples
- *Input:* “We are thrilled to announce…”  
  *Output:* Rewrite using the “confident, plain-spoken” register; remove hype words per the guide.
