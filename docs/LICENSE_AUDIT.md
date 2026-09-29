# Local license metadata audit

**Scope and date:** Direct application dependencies installed from the current lockfiles, inspected locally on 2026-09-28. This is a package metadata and bundled-asset inventory, not a legal opinion or a grant of redistribution rights. Transitive dependencies, container base images and any customer-supplied brand assets need a separate release review.

## Python direct dependencies

Observed in `apps/api/.venv/Lib/site-packages/*dist-info/METADATA` or the bundled license file:

| Package(s) | Observed license metadata |
| --- | --- |
| FastAPI, SQLAlchemy, Alembic, pydantic-settings | MIT |
| LangChain, langchain-core, langchain-openai, LangGraph, langgraph-checkpoint-postgres, LangSmith | MIT |
| pwdlib | METADATA lists a LICENSE file without an SPDX expression; that installed file begins `MIT License`. |
| Uvicorn, pypdf, httpx | BSD-3-Clause |
| ReportLab | METADATA says “BSD license (see license.txt for details)” and includes a LICENSE file; exact redistribution notice should be retained. |
| python-multipart | Apache-2.0 |
| psycopg and installed `psycopg-binary` extra | LGPL-3.0-only; redistribution obligations need explicit review before packaging. |

The production `pyproject.toml` also declares a Python runtime and optional development packages. This table covers named direct runtime packages and the installed psycopg binary extra; it does not audit the entire transitive environment or development-only tools.

## Frontend direct dependencies

Observed `license` fields in installed `apps/web/node_modules/*/package.json`:

| Package(s) | Observed license field |
| --- | --- |
| React, React DOM, TanStack Query, Tailwind CSS, `@tailwindcss/vite`, Vite, `@vitejs/plugin-react`, `@types/node`, `@types/react`, `@types/react-dom`, ESLint `10.11.0`, `@eslint/js` `10.0.1`, `typescript-eslint` `8.70.1` | MIT |
| lucide-react | ISC |
| TypeScript, Playwright `1.62.1` (development-only browser test dependency) | Apache-2.0 |

The Playwright and three lint-package license fields were read from their installed `apps/web/node_modules` package metadata. They are development dependencies; this does not by itself determine what a distributed bundle contains. Playwright's transitive `playwright-core` and browser binaries are outside this direct-package audit. The web UI uses Lucide icons through `lucide-react`. Its CSS uses system font stacks and no externally fetched font was identified in the current source. The PDF renderer uses ReportLab's built-in Helvetica family; no separate font file or stock image is intentionally bundled. Recheck the final built asset directory before distribution, because a later design change may add files.

## Release action

Before redistributing a customer installation or source bundle, collect and retain the actual license/notice files for direct and transitive packages, verify base-image licenses and notices, review LGPL obligations for psycopg packages, and confirm rights for any customer-provided logo, copy, imagery or terms. Document the decision and notices with the released artifact. This audit is evidence of locally observed metadata only.
