# Plan de desarrollo — `eltoque-python` v0.1.0

> Basado en `CLAUDE.md` (revisado 2026-10-22). Cubre desde el scaffold vacío hasta un
> repositorio listo para compartir (Milestone A + preparación de Milestone C).
> Milestone B (tipado de campos reales) queda fuera hasta tener un token autorizado.

**Estado inicial:** el directorio solo contiene `CLAUDE.md` y `.idea/`. No es repositorio Git.
**Herramientas locales detectadas:** Python 3.14, `uv`, `git`.

---

## 1. Principios que guían el plan

1. **Cada commit deja el repo en verde**: `ruff check`, `ruff format --check`, `mypy src`, `pytest`.
2. **Código y tests viajan juntos** en el mismo commit; nunca "feat ahora, tests después".
3. **De adentro hacia afuera**: primero piezas puras sin red (errores, config, fechas, modelos),
   luego transporte compartido, luego clientes sync/async, luego docs/CI/release.
4. **Sin token real** en ninguna fase. Todo con `httpx.MockTransport` y fixtures sintéticas.
5. **No inventar**: un solo endpoint (`GET /v1/trmi`), `RatesResponse.data` sin tocar.
6. **Nada externo sin aprobación**: no crear repo remoto, no publicar en PyPI, no pedir API key.

---

## 2. Estrategia de commits

### 2.1 Convención: Conventional Commits

```
<tipo>(<scope>): <resumen en imperativo, inglés, ≤72 caracteres>

<cuerpo opcional: el porqué, decisiones, limitaciones conocidas>

Co-Authored-By: ...   # si aplica
```

| Tipo | Uso |
| --- | --- |
| `chore` | Scaffold, configuración de herramientas, archivos de repo sin impacto en el paquete |
| `build` | `pyproject.toml`, dependencias, `uv.lock`, empaquetado |
| `feat` | Funcionalidad pública nueva del SDK |
| `fix` | Corrección de un comportamiento ya commiteado |
| `refactor` | Cambio interno sin cambio de comportamiento |
| `test` | Tests que no acompañan a un `feat`/`fix` (endurecimiento, cobertura, paridad) |
| `docs` | README, `docs/`, ejemplos, docstrings sustanciales |
| `ci` | Workflows de GitHub Actions, Dependabot |
| `security` → usar `fix(security)` o `feat(security)` | Mantener el set estándar de tipos |

**Scopes:** `repo`, `build`, `config`, `errors`, `dates`, `models`, `transport`, `retry`,
`client`, `async`, `api`, `examples`, `readme`, `docs`, `ci`, `release`.

### 2.2 Ramas

- `main` es la rama estable; siempre en verde.
- Una rama corta por fase: `chore/scaffold`, `feat/core-primitives`, `feat/transport`,
  `feat/sync-client`, `feat/async-client`, `test/hardening`, `docs/readme-and-guides`,
  `chore/community-files`, `ci/pipelines`, `release/0.1.0`.
- Integración con **merge `--ff-only` o rebase** para conservar los commits atómicos
  (no squash: el historial por commit es parte del valor del proyecto).
- Mientras no exista remoto, las ramas son locales. Cuando el dueño cree el repo en GitHub:
  proteger `main`, exigir CI verde y PRs.

### 2.3 Reglas de higiene

- Antes de cada commit: `uv run ruff format . && uv run ruff check . && uv run mypy src && uv run pytest -q`.
- Revisar `git diff --staged` buscando tokens, emails privados o datos reales de tasas.
- Nunca `git add -A` a ciegas; `.env`, `dist/`, `.venv/`, `.idea/` en `.gitignore` desde el commit 1.
- Commits pequeños (idealmente < ~400 líneas de diff, salvo docs grandes).
- Tags: solo `v0.1.0` (y opcionalmente `v0.1.0rc1` para TestPyPI) al final; tag anotado.
- `CHANGELOG.md` sigue *Keep a Changelog*; se actualiza en la sección `Unreleased` cuando
  un commit `feat`/`fix` cambia comportamiento visible.

---

## 3. Fases, tareas y commits

Cada fase lista: objetivo → tareas → **commits previstos (en orden)** → criterio de salida.

### Fase 0 — Verificación y decisiones previas (sin commits de código)

**Objetivo:** confirmar el contrato y dejar registradas las decisiones abiertas.

- Revisar en vivo (sin token) `https://tasas.eltoque.com/static/swagger.json`, `/docs/` y los
  términos de uso; anotar diferencias respecto a la tabla de `CLAUDE.md` §2.
- Comprobar disponibilidad en PyPI de `eltoque-python` y que no exista un paquete que
  provea el import `eltoque`.
- Elegir versiones actuales y compatibles de `httpx`, `pytest`, `pytest-cov`, `pytest-asyncio`
  (o `anyio`), `ruff`, `mypy`, `build`, `twine`.
- **Decisiones del dueño** (se pueden posponer a la Fase 10 usando placeholders):
  owner de GitHub, nombre definitivo en PyPI, nombre/contacto público del mantenedor,
  licencia (MIT recomendada).

**Salida:** notas para `docs/api-contract.md` (se commitean en Fase 1).

---

### Fase 1 — Scaffold del repositorio (`chore/scaffold`)

**Objetivo:** paquete vacío instalable con todas las herramientas de calidad funcionando.

Tareas:
- `git init -b main`.
- `.gitignore` (Python, venvs, `dist/`, `.env`, `.idea/`, caches), `.editorconfig`.
- `LICENSE` (MIT, nombre del titular como placeholder si aún no está decidido).
- `pyproject.toml`: PEP 621, Hatchling, `requires-python = ">=3.11"`, versión `0.1.0`,
  dependencia `httpx>=X,<Y`, extra/grupo `dev`, configuración de ruff, mypy (`strict`),
  pytest y coverage (`fail_under = 90`).
- `src/eltoque/__init__.py` (con `__version__`), `src/eltoque/py.typed`.
- `tests/test_public_api.py` mínimo (import + versión).
- `uv.lock` para reproducibilidad de dev.
- `docs/api-contract.md` con checklist verificado / no verificado y URLs fuente.

Commits:
1. `chore(repo): initialize repository with gitignore and editorconfig`
2. `chore(repo): add MIT license`
3. `build: add pyproject with hatchling, src layout and httpx dependency`
4. `build: configure ruff, mypy, pytest and coverage`
5. `feat(api): add eltoque package skeleton with version and py.typed marker`
6. `build: add uv lockfile for reproducible dev environment`
7. `docs(api): record verified and unverified elTOQUE API contract`

**Salida:** `uv sync && uv run pytest` pasa; `uv run python -m build` genera wheel y sdist.

---

### Fase 2 — Primitivas del núcleo, sin red (`feat/core-primitives`)

**Objetivo:** todas las piezas puras y testeables de forma aislada.

Tareas:
- `exceptions.py`: jerarquía completa de `CLAUDE.md` §4 (`ElToqueError` → configuración,
  validación, red, timeout, decode, API → 400/401/422/429/5xx). Atributos: `status_code`,
  `body_excerpt` (truncado y seguro), `rate_limit`, `retry_after`. Sin token en `str`/`repr`.
- `_config.py`: dataclass congelada con validación de token (no vacío, sin espacios ni
  caracteres de control), `repr` redactado, validación de `base_url` (HTTPS obligatorio;
  `http://` solo para `localhost`/`127.0.0.1` y explícito), `timeout`, `max_retries` (default 0)
  y límites (máx. reintentos, delay total).
- `_dates.py`: solo `datetime` naive; formato `YYYY-MM-DD HH:MM:SS`; rechaza aware,
  `from >= to`, ventana `>= 24h`, un solo extremo; helper para un `date` → 00:00:00–23:59:59.
- `models.py`: `RateLimitInfo` (parseo tolerante de `X-RateLimit-*` y `Retry-After`;
  valores malformados → `None`) y `RatesResponse` (`data: Any` intacto, `status_code`,
  `rate_limit`, `received_at` como metadatos del SDK).

Commits:
1. `feat(errors): add ElToqueError exception hierarchy`
2. `feat(config): add validated client configuration with redacted token`
3. `feat(config): validate base_url scheme and restrict plain http to loopback`
4. `feat(dates): validate and format naive datetime ranges under 24 hours`
5. `feat(dates): add single-day range helper with documented timezone ambiguity`
6. `feat(models): add RateLimitInfo with tolerant header parsing`
7. `feat(models): add RatesResponse envelope preserving raw provider JSON`

**Salida:** `tests/test_errors.py`, `test_dates.py`, `test_rate_limits.py` y tests de config en
verde; cobertura de estos módulos ≥ 95 %.

---

### Fase 3 — Transporte compartido (`feat/transport`)

**Objetivo:** lógica común sync/async para construir requests e interpretar responses.

Tareas (`_transport.py`):
- Construcción de request: `GET /v1/trmi`, query params, `Authorization: Bearer`,
  `User-Agent: eltoque-python/<versión>`, `Accept: application/json`.
- Mapeo status → excepción (400/401/422/429/5xx/otros 3xx-4xx → `ElToqueAPIError`).
- Decodificación JSON estricta: JSON inválido o vacío → `ElToqueDecodeError`; nunca `{}`.
  Soportar objeto/lista/escalar/`null` tal cual.
- Límite de tamaño de respuesta (p. ej. 5 MiB) leyendo en streaming.
- Redirecciones desactivadas (`follow_redirects=False`); un 3xx se reporta como error
  sin reenviar el token.
- Política de reintentos pura (sin dormir): decide si reintentar (solo 429/5xx
  transitorios/errores de transporte, nunca 400/401/422), calcula delay respetando
  `Retry-After` con tope por intento y total.
- Traducción de `httpx.TimeoutException` / `httpx.TransportError` a errores del SDK.

Commits:
1. `feat(transport): build authenticated trmi requests with sdk user agent`
2. `feat(transport): map http status codes to sdk exceptions`
3. `feat(transport): decode json strictly and bound response size`
4. `feat(transport): disable redirects to avoid leaking bearer token`
5. `feat(retry): add bounded retry policy honoring Retry-After`

**Salida:** `tests/test_transport.py` en verde, sin dependencia de un cliente concreto.

---

### Fase 4 — Cliente síncrono (`feat/sync-client`)

**Objetivo:** `ElToqueClient` completo.

Tareas (`_client.py`):
- Constructor: `api_token`, `timeout`, `max_retries`, `base_url`, `http_client`
  (inyectado, **no se cierra** si es del llamador), `transport` (seam de tests).
- Métodos: `get_latest_rates()`, `get_rates(date_from, date_to)`, `get_rates_for_day(day)`.
- `with`, `close()`, idempotencia de `close()`, `ElToqueError` claro al usar tras cerrar.
- Bucle de reintentos con `time.sleep` usando la política de la Fase 3.
- Exportar en `__init__.py` solo superficie pública (`__all__`).

Commits:
1. `feat(client): add ElToqueClient with latest and ranged rate methods`
2. `feat(client): support context manager and strict close semantics`
3. `feat(client): honor injected http client ownership`
4. `feat(client): add opt-in bounded retries`
5. `feat(client): add get_rates_for_day convenience method`
6. `feat(api): export public client, models and exceptions`

**Salida:** `tests/test_client.py` cubre path, params, headers, timeouts, errores, cierre,
ownership y reintentos.

---

### Fase 5 — Cliente asíncrono (`feat/async-client`)

**Objetivo:** `AsyncElToqueClient` con semántica idéntica.

Tareas (`_async_client.py`):
- Mismos parámetros y métodos con `async`/`await`, `async with`, `aclose()`.
- Reintentos con `asyncio.sleep` (cancelable; la cancelación se propaga sin envolver).
- Tests de paridad parametrizados: el mismo escenario se ejecuta contra ambos clientes.

Commits:
1. `feat(async): add AsyncElToqueClient mirroring sync API`
2. `feat(async): add async context manager and aclose semantics`
3. `feat(async): add cancellation-safe retries with asyncio.sleep`
4. `test(async): add sync/async parity test suite`

**Salida:** `tests/test_async_client.py` + paridad en verde.

---

### Fase 6 — Endurecimiento y seguridad (`test/hardening`)

**Objetivo:** cerrar la matriz de pruebas de `CLAUDE.md` §7.

Tareas:
- Token nunca presente en mensajes de excepción, `repr`, logs (`caplog`) ni salida de pytest.
- Inyección de headers (`\r\n`, `\x00`, espacios) rechazada.
- Redirect a otro host: verificar que no hay segunda request con `Authorization`.
- Errores de conexión, DNS, connect/read timeout.
- Concurrencia simulada con 429 (async `gather` acotado); ausencia de polling en segundo plano.
- Test de integración **opt-in** (`-m integration`), saltado salvo `ELTOQUE_API_TOKEN`
  + variable de autorización explícita; excluido del CI.
- Revisar cobertura real ≥ 90 % sin exclusiones artificiales.

Commits:
1. `test(security): assert tokens never leak into errors, repr or logs`
2. `test(transport): cover network, dns and timeout failure modes`
3. `test(transport): verify cross-host redirects do not forward credentials`
4. `test(async): simulate concurrent requests under rate limiting`
5. `test: add opt-in integration test skipped without authorized token`
6. `fix(...)`: los que surjan de esta fase, uno por defecto encontrado

**Salida:** cobertura ≥ 90 %, `mypy --strict` limpio.

---

### Fase 7 — Documentación y ejemplos (`docs/readme-and-guides`)

**Objetivo:** documentación precisa, atractiva y verificada.

Tareas:
- `README.md` siguiendo la secuencia de 16 puntos de `CLAUDE.md` §6 (disclaimer no oficial
  y atribución arriba; instalación local honesta; sin badges rotos).
- `docs/quickstart.es.md`, `configuration.md`, `errors.md`, `security.md`
  (`publishing.md` llega en Fase 9).
- `examples/basic.py`, `async_basic.py`, `date_range.py` (+ `fastapi_integration.py` opcional).
- Test que ejecuta los bloques de código del README y los ejemplos contra `MockTransport`
  (garantiza que coinciden con la API real).

Commits:
1. `docs(readme): write README with disclaimer, quickstart and api reference`
2. `docs: add Spanish quickstart guide`
3. `docs: add configuration, errors and security guides`
4. `docs(examples): add sync, async and date range examples`
5. `test(docs): execute README snippets and examples against mock transport`

**Salida:** `twine check` del README pasa; todos los snippets ejecutados en tests.

---

### Fase 8 — Archivos de comunidad (`chore/community-files`)

Tareas: `CHANGELOG.md`, `CONTRIBUTING.md` (setup, comandos, convención de commits de este
plan), `CODE_OF_CONDUCT.md` (Contributor Covenant), `SECURITY.md` (reporte privado vía
GitHub Security Advisories, sin email personal), `.env.example` con placeholder falso,
`.github/ISSUE_TEMPLATE/` (bug, feature) y `pull_request_template.md`.

Commits:
1. `docs: add changelog with unreleased 0.1.0 entries`
2. `docs: add contributing guide and code of conduct`
3. `docs: add security policy and env example with fake placeholder`
4. `chore(repo): add issue and pull request templates`

---

### Fase 9 — CI/CD (`ci/pipelines`)

Tareas:
- `.github/workflows/ci.yml`: PR + push a `main` + `workflow_dispatch`; matriz 3.11–3.14;
  `permissions: contents: read`; ruff, format check, mypy, pytest con cobertura,
  `python -m build`, `twine check`; job de **smoke test** que instala el wheel en un venv
  limpio fuera del repo e importa/ejecuta un ejemplo con mock. Actions fijadas por SHA.
- `.github/dependabot.yml` (pip/uv + github-actions).
- `.github/workflows/publish.yml`: disparo por tag `v*` o manual; job `build` → job
  `publish` con `environment: pypi`, `id-token: write` solo ahí,
  `pypa/gh-action-pypi-publish`; verificación tag == versión del paquete. TestPyPI
  opcional en job separado y también protegido. **No se activa** hasta que el dueño
  configure Trusted Publishing.
- `docs/publishing.md`: pasos manuales para el dueño.

Commits:
1. `ci: add quality matrix workflow for python 3.11-3.14`
2. `ci: add built wheel smoke test in isolated environment`
3. `ci: add dependabot for dependencies and actions`
4. `ci(release): add gated trusted publishing workflow`
5. `docs: add publishing guide for trusted publisher setup`

**Salida:** workflows validados localmente (sintaxis con `actionlint` si está disponible);
la ejecución real queda pendiente de que exista el remoto.

---

### Fase 10 — Preparación de release (`release/0.1.0`)

Tareas:
- Ejecutar la checklist completa de `CLAUDE.md` §8 y §11.
- Verificar contenido del wheel (`py.typed`, `LICENSE`, metadata) con `unzip -l`.
- Instalar el wheel en venv limpio, importar desde fuera del repo.
- Resolver placeholders (owner, URLs del proyecto, mantenedor) con el dueño; añadir
  badges reales **solo** si ya existen CI y PyPI.
- Mover `Unreleased` → `0.1.0 — <fecha>` en el changelog.
- Tag anotado local `v0.1.0` (no push sin aprobación).

Commits:
1. `build(release): set project urls and maintainer metadata`
2. `docs(readme): add badges for existing ci and package index`  *(si aplica)*
3. `chore(release): prepare 0.1.0`
4. Tag: `git tag -a v0.1.0 -m "eltoque-python 0.1.0"`

**Salida = "listo para compartir":** se cumple todo el checklist de `CLAUDE.md` §11.

---

## 4. Acciones manuales del dueño (fuera del alcance de Claude)

| Momento | Acción |
| --- | --- |
| Antes de Fase 10 | Confirmar owner de GitHub, nombre PyPI, nombre público del mantenedor, licencia |
| Tras Fase 10 | Crear repo en GitHub, `git push -u origin main --tags`, proteger `main` |
| Tras primer CI verde | Crear proyecto en PyPI (o *pending publisher*) y configurar Trusted Publisher (owner/repo/`publish.yml`/environment `pypi`) |
| Publicación | Crear environment `pypi` con aprobación requerida; publicar solo por decisión explícita |
| Milestone B | Registrar su propia aplicación en https://tasas-token.eltoque.com/ y autorizar verificación del esquema 200 |

---

## 5. Milestone B (futuro, requiere token autorizado)

1. Pocas requests autorizadas para observar el esquema HTTP 200.
2. Documentar en `docs/api-contract.md` un ejemplo **sanitizado** y la fecha de validación.
3. Modelos tipados con `Decimal` solo para campos confirmados, conservando `data` crudo.
4. Commits: `docs(api): record verified 200 response schema`,
   `feat(models): add typed decimal rate model for confirmed fields`, release `0.2.0`.

---

## 6. Resumen de ritmo

| Fase | Rama | Commits aprox. |
| --- | --- | --- |
| 1 Scaffold | `chore/scaffold` | 7 |
| 2 Primitivas | `feat/core-primitives` | 7 |
| 3 Transporte | `feat/transport` | 5 |
| 4 Cliente sync | `feat/sync-client` | 6 |
| 5 Cliente async | `feat/async-client` | 4 |
| 6 Endurecimiento | `test/hardening` | 5 + fixes |
| 7 Docs | `docs/readme-and-guides` | 5 |
| 8 Comunidad | `chore/community-files` | 4 |
| 9 CI/CD | `ci/pipelines` | 5 |
| 10 Release | `release/0.1.0` | 2–3 + tag |
| **Total** | | **~50 commits** |
