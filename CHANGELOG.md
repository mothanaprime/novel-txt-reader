# Changelog

## 0.1.2 — Unreleased

- Validate a complete progress backup before changing saved data, reject wrong-book
  backups, and render imported bookmark values safely.
- Scope progress to each book, retain legacy storage for confirmed migration, and use
  the actual book title in exported filenames.
- Keep the current chapter and position when loading another chapter fails; correct
  progress percentages for the final chapter and single-chapter books.
- Make closed panels unavailable to keyboard focus and provide keyboard-accessible
  chapter navigation.
- Preserve prose containing URLs and avoid treating ordinary sentences as volume or
  special-section headings.
- Decode strictly, detect supported legacy encodings conservatively, and add an explicit
  `--encoding` override instead of silently producing replacement characters.
- Stage generated output, preserve unrelated files, and roll back ordinary promotion
  errors during rebuilds.
- Add exact-text Python regression tests, real-browser offline tests, and CI with fixed
  browser-test dependencies.
- Document Claude, Codex, and official DeepSeek Harness (DSH) setup, including a shared
  standalone skill installation, host prerequisites, and verification limits.
- Resolve script paths from the loaded skill directory in the skill instructions,
  include Windows commands, and distinguish standalone tests from repository-only tests.
- Add Chinese usage, installation, and plugin guides with language navigation; document
  the shared main branch and the distinction between merging changes and publishing releases.

## 0.1.1

- Add a scroll-to-bottom button beside the scroll-to-top button.

## 0.1.0

- Initial offline TXT reader and installable plugin marketplace.
