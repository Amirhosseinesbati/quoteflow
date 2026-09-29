# Dependencies and versions

The product requirements specifies Python/FastAPI/Pydantic/SQLAlchemy/Alembic/PostgreSQL/LangChain/LangGraph for the API and React/TypeScript/Vite/Tailwind plus a query/cache layer for the client. Dependencies must be resolved from current compatible releases, pinned in Python and JavaScript lockfiles, and container images must use exact tags. This file records **tested** versions only after lockfile installation and checks; a package declaration alone is not a tested version.

## Version ledger

| Component | Declared/locked | Tested runtime | Evidence |
| --- | --- | --- | --- |
| Python | API image declares `3.12.11-slim-bookworm`; `pyproject.toml` requires `>=3.12` | Bundled Python `3.12.13` ran generator/fixture checks; Compose API image built and ran | Exact Python version inside container not separately recorded |
| FastAPI, Pydantic, SQLAlchemy, Alembic | `0.141.1`, `2.13.5`, `2.1.1`, `1.20.0` in `apps/api/uv.lock` | Installed on Python 3.12.13 with `uv sync --all-extras`; 22 backend tests passed; Compose/PostgreSQL 17.10 migration through `a4b1c9d2e3f4` and live API/workflow paths passed | Connected adapters remain unverified |
| LangChain, LangGraph and checkpoint driver | LangChain `1.4.2`, LangGraph `1.2.12`, checkpoint-postgres `3.1.2` in `apps/api/uv.lock` | In-memory graph test and live PostgreSQL workflow restart/resume to completion passed; 16 checkpoints for that job | Actual process-crash/concurrent-worker behavior pending |
| PostgreSQL image | `postgres:17.10-alpine3.22` in Compose | Image built/started; migration, seeded counts, live workflow and custom-format dump/restore passed; separate local PDF asset tar/extraction passed byte comparison | Coordinated separate-installation restore and customer deployment pending |
| Node.js | Build image `node:22.19.0-bookworm-slim` | `v24.18.0` observed on build host; Compose web image built and served HTTP 200 | Container Node version not separately queried |
| pnpm | `11.19.0`, declared and frozen in web package/lockfile | `11.19.0` installed web dependencies; `pnpm lint`/`pnpm build` passed; Compose web image built | Hosted CI result pending |
| React, TypeScript, Vite, Tailwind, query layer | React `19.3.0`, TypeScript `5.9.3`, Vite `8.3.1`, Tailwind `4.3.3`, TanStack Query `5.104.0` in web package/lockfile | `pnpm build` passed TypeScript `--noEmit` and Vite (1,941 modules; 1.02 s); Compose web HTTP 200 and browser path to acceptance passed | Broader browser/accessibility matrix pending |
| Frontend lint | ESLint `10.11.0`, `@eslint/js` `10.0.1`, `typescript-eslint` `8.70.1` resolved in web lockfile; `eslint.config.mjs` uses their recommended flat configs | `pnpm lint` (`eslint src`) passed on Windows 2026-09-28; config targets `src/**/*.{ts,tsx}` | CI job declares lint before build; hosted CI result not recorded |
| PDF renderer and browser automation | ReportLab `4.5.1`, pypdf `6.19.0` in `apps/api/uv.lock`; Playwright `1.62.1` in web devDependencies/lockfile | Two-page PDF and four-page stress render inspected; browser tests passed on SQLite and Compose/PostgreSQL; published PDF remained downloadable after API restart (HTTP 200, 4,805 bytes); three local PDF assets passed archive/restore byte comparison | Multilingual PDF and coordinated installation restore pending |

Other resolved Python versions relevant to the pilot include `uvicorn 0.54.0`, `psycopg 3.3.6`, `langchain-openai 1.6.6`, `httpx 0.28.1`, `pytest 9.1.1` and `ruff 0.16.9`. The local checks above demonstrate selected runtime paths, not general deployment compatibility.

On this Windows host, the `npm` command points to a missing user installation; use pnpm for the client. Docker daemon was initially unavailable but later ran the Compose stack. `uv` may require `UV_CACHE_DIR` set to a writable workspace path for installation here. The Compose web image uses nginx `1.29.1-alpine3.22`. Port 8080 was occupied, so this host uses an ignored `.env` with `QUOTEFLOW_PORT=8082`; Compose resolves the public/API URLs accordingly. These are local host observations, not a universal port or compatibility guarantee.

## Reproducibility requirements

- Commit exact dependency lockfiles and verify clean installation from them.
- Use exact image tags in Compose; record image digest if the deployment process requires reproducible rebuilds.
- Record Python, Node, pnpm, PostgreSQL and browser versions with actual command output from CI/local acceptance.
- Rebuild the typed client from the API OpenAPI schema or check it for drift in CI.
- Run Python lint/type/test, frontend lint/type/build, migration tests and integration/contract tests in CI.
- Check licenses of bundled fonts, icons, libraries and any other redistributed assets before customer packaging. Local direct-package metadata observations are in [`LICENSE_AUDIT.md`](LICENSE_AUDIT.md); transitive/base-image and final notice review remain open. A package appearing in a registry is not proof of resale rights.

## API reference policy

Framework API usage should be checked against current official documentation at implementation time, especially LangChain structured output and LangGraph interrupt/checkpoint APIs. Avoid copying old tutorial imports. Record the actual checked package versions and compatibility results in this ledger.
