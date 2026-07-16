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

`scripts/publish_from_obsidian.py` copies a note from the Obsidian vault at `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/lizchen/BagelNotes` into this repo. The vault has `blog/` and `note/` subfolders; the script auto-detects which collection to publish into based on which subfolder the source file is in (falls back to an interactive prompt otherwise). For `blog`, it also prompts for a title/description if missing and generates a slug for the filename. It never modifies the original Obsidian file, and only writes into `src/content/{blog,notes}/` — a separate `git add/commit/push` is required to actually publish.

Other one-off scripts in `scripts/` (`download-sketchbook.py`, `import-wordpress.py`) were used for the original WordPress-to-Astro migration and image hosting; not part of the regular workflow.

### Other pages

`src/pages/about.astro`, `blog-roll.astro`, and `sketchbook.astro` are standalone static pages. Site-wide nav is defined in `src/components/Header.astro`; global CSS variables (colors, fonts) live in `src/styles/global.css`.
