# URL Route — Omarchy Theme Sync

## Store pages

- [Firefox Add-ons (AMO)](https://addons.mozilla.org/en-US/firefox/addon/url-route-omarchy-theme-sync/)
- [Thunderbird Add-ons (ATN)](https://addons.thunderbird.net/en-US/thunderbird/addon/url-route-omarchy-theme-sync/)

The separately installed local companion is required on Linux with Omarchy and Python 3.11 or later.

## Development and release notes

The current store-review candidate synchronizes application theme colors with Omarchy on desktop Linux. It does **not** provide the legacy URL-copy/history/webhook functionality.

**Do not submit or load the root `manifest.json`.** It belongs to the preserved, unreviewed legacy prototype. The reviewed theme-only sources are in `src/theme-sync/` and the release builder is `scripts/build_store_release.py`.

Current targets: **Firefox 0.3.0 (unchanged)** and **Thunderbird 0.3.1 (platform-package correction)**. Use only `url-route-thunderbird-store-review-0.3.1.xpi` for the Thunderbird update; never upload the Firefox XPI to ATN. Submission candidates, their source archive, the separate native companion and validation evidence are under `build/store-release/`. These are unsigned review candidates, not store-approved releases. Linux, Omarchy and the separately installed Python 3.11+ companion are required.

The detailed review, privacy-policy draft, listing draft and publication checklist are maintained in the Obsidian vault notes named **URL Route - Store Submission Review**, **URL Route - Privacy Policy Draft** and **URL Route - Store Listing Draft**. Reproducible build and companion installation instructions are also included in the review archives.

Author: **Guiestrela**. Main-code license: **MIT** (see `LICENSE`). The icon retains its upstream license notice. Support: **guilhermestrela@gmail.com**. GitHub: **guiestrela**. Repository and companion source: https://github.com/guiestrela/url-copy-fire. The owner-provided Firefox dashboard shows version 0.3.0 awaiting review. Thunderbird compatibility is limited to the tested 158 branch (158.0 through 158.*); the owner provided an Approved/listed 0.3.0 dashboard and public ATN listing. Local inspection then found the installed 0.3.0 XPI byte-identical to the Firefox candidate, without Thunderbird theme-experiment mappings. The remote download was not independently retrieved. Thunderbird 0.3.1 restores the correct target and passed isolated actual-toolbar and semantic-notification QA; this new update has not been uploaded or approved. A packaged companion GitHub Release has not been published yet.
