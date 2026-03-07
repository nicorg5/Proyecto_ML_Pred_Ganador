# GitHub Actions Workflows

## Estrategia de Branching (Git Flow)

```
master       → Producción (código estable, deployable)
   ↑
develop      → Pre-producción / Integración (código validado)
   ↑
feature/*    → Desarrollo de features específicas
```

## Workflow: CI/CD Pipeline

**Archivo**: `ci.yml`

### Triggers

- **Push**: `master`, `develop`, `feature/**`
- **Pull Request**: hacia `master` o `develop`

### Jobs

| Job | Descripción | Se ejecuta en |
|-----|-------------|---------------|
| **lint** | Ruff + Black formatting | Todas las ramas |
| **test** | Pytest (unit + integration) con matrix Python 3.10/3.11/3.12 | Todas las ramas |
| **type-check** | MyPy type checking | Todas las ramas |
| **security** | Bandit security scan | Todas las ramas |
| **build** | Build package con UV | Solo push a `master` |

### Flujo de Trabajo

1. **Feature Branch** (`feature/nueva-funcionalidad`)
   - Se ejecutan: lint + test + type-check + security
   - NO se ejecuta: build

2. **Develop Branch** (pre-producción)
   - Se ejecutan: lint + test + type-check + security
   - NO se ejecuta: build

3. **Master Branch** (producción)
   - Se ejecutan: lint + test + type-check + security + **build**
   - Genera artifacts distribuibles

### Protección de Ramas (Recomendado)

**Master**:
- ✅ Require PR antes de merge
- ✅ Require status checks: `lint`, `test`, `type-check`
- ✅ Require branch up to date

**Develop**:
- ✅ Require PR antes de merge
- ✅ Require status checks: `lint`, `test`

**Feature**:
- ❌ Sin protección (desarrollo libre)

## Codecov Integration

El workflow sube cobertura de código a Codecov.io. Configurar:

1. Registrarse en https://codecov.io con GitHub
2. Añadir repositorio
3. Copiar token en GitHub: Settings → Secrets → `CODECOV_TOKEN`