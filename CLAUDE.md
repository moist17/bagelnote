# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
npm run dev        # local dev server at localhost:4321
npm run build      # production build to ./dist/
npm run preview    # preview the production build locally
npm run astro check   # type-check .astro files and content collection schemas
```

There is no test suite or linter configured in this project.

## Architecture

This is an Astro blog (bagelnote-astro), migrated from a previous Hugo-based version of the same site (`bagelnote`, a sibling directory — not this repo). Deployed via GitHub Actions (`.github/workflows/deploy.yml`) to GitHub Pages on every push to `main`; custom domain is `lizchen.co` (see `public/CNAME`).

### Content collections

Two Astro content collections are defined in `src/content.config.ts`, both loaded via `glob()`:

- **`blog`** (`src/content/blog/*.md`) — long-form posts. Schema requires `title`, `description`, `pubDate`, with optional `updatedDate` and `heroImage`.
- **`notes`** (`src/content/notes/*.md`) — short-form "pulse"-style posts. Schema only requires `pubDate`; the markdown body is the post itself, no title.

Routing: `src/pages/blog/index.astro` and `src/pages/blog/[...slug].astro` render the blog list and individual posts (using `src/layouts/BlogPost.astro`). `src/pages/notes.astro` renders all notes as a single reverse-chronological feed on one page — notes do not have individual permalinks by design.

### Publishing from Obsidian

`scripts/publish_from_obsidian.py` copies a note from the Obsidian vault at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/lizchen/BagelNotes` into this repo and publishes it — fully automated, no prompts, no confirmation step. It's designed to be triggered from Obsidian itself (e.g. via the community "Shell commands" plugin bound to a hotkey/ribbon button), so it never blocks on stdin.

```sh
python scripts/publish_from_obsidian.py <Obsidian 筆記檔名>            # publish/update
python scripts/publish_from_obsidian.py <Obsidian 筆記檔名> --delete   # unpublish
```

- The vault has `blog/` and `note/` subfolders; the script detects which collection to publish into based on which subfolder the source file is in. Files outside both folders are rejected with an error (no interactive fallback, since there's no one to prompt).
- The output filename is derived from the **Obsidian source filename** (slugified), not the title — this makes it stable across edits, so re-running the script on an edited note overwrites/updates the same published file instead of creating a duplicate.
- `blog` posts read `title`/`description` from the source note's own frontmatter (not prompted). Missing `description` aborts the whole run before writing or pushing anything, since the content collection schema requires it. On update, the original `pubDate` is preserved and `updatedDate` is set to today.
- `note` posts have no title/description; on update, the original `pubDate` is preserved (notes don't have an `updatedDate` field).
- On publish it runs `git add` + `commit` + `push` automatically; `--delete` looks up the previously-published file for that source note and runs `git rm` + `commit` + `push`. Either mode aborts loudly (non-zero exit) rather than partially completing if a git step fails.
- It never modifies or deletes the original Obsidian file — only files under `src/content/{blog,notes}/` are touched.
- Obsidian-side templates prefilling the expected frontmatter live in the vault at `templates/blog-template.md` and `templates/note-template.md`.

Other one-off scripts in `scripts/` (`download-sketchbook.py`, `import-wordpress.py`) were used for the original WordPress-to-Astro migration and image hosting; not part of the regular workflow.

## Conventions

- All git commit messages must be written in English.

### Other pages

`src/pages/about.astro`, `blog-roll.astro`, and `sketchbook.astro` are standalone static pages. Site-wide nav is defined in `src/components/Header.astro`; global CSS variables (colors, fonts) live in `src/styles/global.css`.
