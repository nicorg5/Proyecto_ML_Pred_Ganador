# 🚀 DEPLOYMENT - LaLiga Predictor en Render

**Estado**: Phase 5.5 - Deploy en Render  
**Última actualización**: 15 de mayo, 2026  
**Autor**: Nicolas

---

## 📋 Requisitos Previos

- ✅ Cuenta en [Render.com](https://render.com)
- ✅ GitHub conectado a Render (autenticación OAuth)
- ✅ Repositorio en GitHub con rama `develop` actualizada
- ✅ Todos los commits hechos (no hay cambios pendientes)

---

## 🔧 PASO 1: Hacer Push de los Cambios

Desde tu máquina local, sube los commits:

```bash
git push origin develop
```

Esto enviará todos los commits de Phase 5.4 al repositorio.

**Commits que se subirán:**
1. feat: Actualizar lista de equipos a La Liga 2025/26
2. fix: Corregir schema HealthResponse
3. fix: Agregar libgomp1 a Dockerfile
4. chore: Actualizar docker-compose.yml
5. docs: Marcar Fase 5.4 completada
6. feat: Agregar frontend React 19 + Vite

---

## 🌐 PASO 2: Crear Web Service para Backend en Render

### 2.1 Crear nuevo servicio

1. Abre https://dashboard.render.com/
2. Haz clic en **New +** → **Web Service**
3. Conecta tu repositorio GitHub `Proyecto_ML_Pred_Ganador`
4. Elige la rama: **develop**

### 2.2 Configurar el Backend

**Nombre del servicio:**
```
laliga-predictor-api
```

**Environment:**
```
Docker
```

**Root Directory:**
```
backend
```

**Dockerfile Path:**
```
Dockerfile
```

### 2.3 Configurar variables de entorno

En **Environment** (Render Dashboard), añade:

```
DATABASE_URL=postgresql://[usuario]:[contraseña]@[host]:[puerto]/laliga_predictor
SD_DATABASE_URL=postgresql://[usuario]:[contraseña]@[host]:[puerto]/laliga_soccerdata
PYTHONUNBUFFERED=1
```

**Nota:** Para usar PostgreSQL, tienes estas opciones:
- Usar PostgreSQL de Render (gratis hasta ciertos límites)
- Usar servicio externo (Neon, Supabase, etc.)

### 2.4 Configurar Deploy

**Build Command:**
```
pip install uv && uv pip install --no-cache -r pyproject.toml
```

**Start Command:**
```
uvicorn src.laliga_predictor.api.main:app --host 0.0.0.0 --port 8000
```

**Health Check Endpoint:**
```
/health
```

**Instance Type:** Free (o superior si necesitas mejor performance)

### 2.5 Presionar Deploy

Haz clic en **Deploy**. Render construirá la imagen Docker y desplegarå el servicio.

**Tiempo aproximado:** 5-10 minutos

---

## 🎨 PASO 3: Crear Static Site para Frontend en Render

### 3.1 Crear nuevo servicio

1. Haz clic nuevamente en **New +** → **Static Site**
2. Conecta el mismo repositorio
3. Elige la rama: **develop**

### 3.2 Configurar el Frontend

**Nombre del servicio:**
```
laliga-predictor-web
```

**Root Directory:**
```
frontend
```

**Build Command:**
```
npm install && npm run build
```

**Publish Directory:**
```
dist
```

### 3.3 Configurar Variables de Entorno

En **Environment**, añade:

```
VITE_API_URL=https://laliga-predictor-api.onrender.com
```

(Sustituye `laliga-predictor-api` por el nombre real de tu servicio backend)

### 3.4 Deploy

Haz clic en **Deploy**.

**Tiempo aproximado:** 3-5 minutos

---

## ✅ PASO 4: Verificar Deploy

Una vez ambos servicios estén desplegados:

### 4.1 Verificar Backend

Abre en el navegador:
```
https://laliga-predictor-api.onrender.com/health
```

Deberías ver:
```json
{
  "status": "healthy",
  "models_loaded": {
    "winner": true,
    "goals_ou": 3,
    "cards_ou": 3
  },
  "timestamp": "2026-05-15T16:00:00Z"
}
```

### 4.2 Verificar Teams Endpoint

```
https://laliga-predictor-api.onrender.com/teams
```

Deberías ver los 20 equipos de La Liga 2025/26.

### 4.3 Verificar Frontend

Abre en el navegador:
```
https://laliga-predictor-web.onrender.com
```

Deberías ver la página principal del predictor con:
- Formulario para seleccionar equipos
- Lista de 20 equipos cargada desde el API

### 4.4 Test E2E: Hacer una Predicción

1. Selecciona: Real Madrid (Home) vs Barcelona (Away)
2. Elige una fecha futura
3. Haz clic en "Get Prediction"
4. Verifica que aparezcan las 3 predicciones:
   - 🏆 Winner (H/D/A)
   - ⚽ Goals O/U (1.5, 2.5, 3.5)
   - 🟡 Cards O/U (3.5, 4.5, 5.5)

---

## 🔄 PASO 5: Configurar Auto-Deploy

### 5.1 Habilitar Auto-Deploy en Push

Ambos servicios deberían estar configurados para auto-deployar al hacer push a `develop`.

**Verificar en Render Dashboard:**
- Settings → Deploy Settings
- "Auto-deploy" debe estar activado
- Branch debe ser `develop`

### 5.2 Workflow Post-Deploy

Cada vez que hagas:

```bash
git push origin develop
```

Render automáticamente:
1. Detectará los cambios
2. Reconstruirá las imágenes Docker
3. Desplegará nuevas versiones
4. Apagará las antiguas

**Tiempo total:** 10-15 minutos

---

## 📊 PASO 6: Monitoreo en Producción

### 6.1 Ver Logs

En Render Dashboard:
1. Selecciona cada servicio
2. Haz clic en **Logs**
3. Monitorea en tiempo real

### 6.2 Health Checks

Render revisa automáticamente el endpoint `/health` cada 30 segundos.

Si falla:
- Recibe alertas por email
- El servicio se marca como "unhealthy"
- Se intentan reintentos automáticos

### 6.3 Renovación de Certificados SSL

Render maneja automáticamente certificados HTTPS. No hay acción requerida.

---

## 🐛 Troubleshooting

### El backend no arranca

**Error típico:** `ModuleNotFoundError: No module named 'src.laliga_predictor'`

**Solución:**
```bash
# En Render, el Start Command debe ser:
uvicorn src.laliga_predictor.api.main:app --host 0.0.0.0 --port 8000

# O si eso no funciona, prueba:
python -m src.laliga_predictor.api.main:app --host 0.0.0.0 --port 8000
```

### El frontend no puede conectar al API

**Error típico:** `ERR_CONNECTION_REFUSED` o `CORS error`

**Solución:**
1. Verifica que `VITE_API_URL` apunta a la URL correcta del backend en Render
2. El backend debe tener CORS habilitado (ya está configurado en main.py)
3. Espera a que ambos servicios estén `healthy`

### Build falla en Render

**Motivo común:** Timeout por dependencias lentas

**Solución:**
1. Aumenta el Build Plan a "Pro" si es necesario
2. Cachea dependencias npm:
   ```bash
   npm ci --prefer-offline --no-audit
   ```

### Modelos no cargados

**Error:** `models_loaded.winner: false`

**Solución:**
1. Verifica que el volumen de modelos está montado
2. Ejecuta el entrenamiento localmente
3. Los archivos .joblib deben estar en `backend/models/`

---

## 🎯 Próximos Pasos (Opcional)

### Opción A: Setup CI/CD Avanzado

Crear un workflow GitHub que:
- Ejecute tests al hacer push
- Construya imágenes Docker
- Suba a Docker Registry
- Deploy automático a Render

### Opción B: Database en Producción

Actualmente, Render crea una BD PostgreSQL junto con el servicio.

Para persistencia permanente:
1. Usa Render PostgreSQL (incluido) O
2. Migra a Neon, Supabase, AWS RDS

### Opción C: Monitoreo Avanzado

Integra con:
- Sentry (error tracking)
- DataDog (APM monitoring)
- CloudFlare (CDN para assets estáticos)

---

## 📝 Resumen del Deploy

| Componente | Plataforma | URL | Tiempo |
|-----------|-----------|-----|--------|
| Backend API | Render Web Service | https://laliga-predictor-api.onrender.com | 5-10 min |
| Frontend | Render Static Site | https://laliga-predictor-web.onrender.com | 3-5 min |
| Database | PostgreSQL (Render) | Interno | - |

**Status:** ✅ Listo para producción

---

## 📞 Support

Si encuentras problemas:
1. Revisa los logs en Render Dashboard
2. Verifica las variables de entorno
3. Comprueba que el repositorio está actualizado
4. Reinicia el servicio (Render Dashboard → Service → Restart)

---

**¡Listo para producción! 🚀**
