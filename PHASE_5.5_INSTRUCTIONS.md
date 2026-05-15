# 🚀 PHASE 5.5 - INSTRUCCIONES PARA DEPLOY EN RENDER

**Estado**: Todos los cambios listos para hacer push  
**Fecha**: 15 de mayo, 2026

---

## ✅ Lo que ya está hecho

Hemos completado 7 commits atómicos en la rama `develop`:

1. ✅ `feat: Actualizar lista de equipos a La Liga 2025/26`
2. ✅ `fix: Corregir schema HealthResponse`
3. ✅ `fix: Agregar libgomp1 a Dockerfile`
4. ✅ `chore: Actualizar docker-compose.yml`
5. ✅ `docs: Marcar Fase 5.4 completada`
6. ✅ `feat: Agregar frontend React 19 + Vite`
7. ✅ `docs: Agregar documentación para Deploy y API`

---

## 📋 Próximos Pasos (TÚ debes hacer esto)

### PASO 1: Hacer Push a GitHub

Desde tu máquina local:

```bash
cd /home/nico/repos/Proyecto_ML_Pred_Ganador
git push origin develop
```

**Resultado esperado:** Los 7 commits aparecen en GitHub rama `develop`

---

### PASO 2: Preparar Render (Cuenta)

1. Ve a https://render.com/
2. Haz clic en **Sign Up**
3. Conecta con GitHub (autoriza acceso)
4. Verifica tu email

---

### PASO 3: Desplegar Backend

En Render Dashboard:

```
New → Web Service
├─ Conectar repo: Proyecto_ML_Pred_Ganador
├─ Rama: develop
├─ Root Directory: backend
├─ Nombre servicio: laliga-predictor-api
└─ Haz clic en Deploy
```

**Tiempo:** 5-10 minutos

**Verificar:** Abre `https://laliga-predictor-api.onrender.com/health`

---

### PASO 4: Desplegar Frontend

En Render Dashboard:

```
New → Static Site
├─ Conectar repo: Proyecto_ML_Pred_Ganador
├─ Rama: develop
├─ Root Directory: frontend
├─ Nombre servicio: laliga-predictor-web
├─ Variable de entorno:
│  VITE_API_URL=https://laliga-predictor-api.onrender.com
└─ Haz clic en Deploy
```

**Tiempo:** 3-5 minutos

**Verificar:** Abre `https://laliga-predictor-web.onrender.com`

---

### PASO 5: Hacer Test E2E (End-to-End)

En el navegador:

1. Abre: `https://laliga-predictor-web.onrender.com`
2. Selecciona: Real Madrid (Home) vs Barcelona (Away)
3. Elige una fecha futura
4. Haz clic en "Get Prediction"
5. Verifica que aparezcan las 3 predicciones:
   - 🏆 Winner (H/D/A)
   - ⚽ Goals (1.5, 2.5, 3.5)
   - 🟡 Cards (3.5, 4.5, 5.5)

**Resultado esperado:** ✅ Todo funciona en producción

---

## 📚 Documentación a Consultar

Hemos creado 2 documentos importantes en `/docs/`:

### 1. `docs/DEPLOYMENT.md`
Guía detallada paso a paso para:
- Crear servicios en Render
- Configurar variables de entorno
- Verificar deploy
- Troubleshooting común
- Auto-deploy configuration

### 2. `docs/API.md`
Documentación completa del API:
- Todos los endpoints
- Schemas de request/response
- Error handling
- Ejemplos en Python, JavaScript, cURL

---

## 🔄 Variables de Entorno Necesarias

### Backend

En Render Dashboard → Service Settings → Environment:

```
DATABASE_URL=postgresql://[user]:[pass]@[host]:[port]/[db]
SD_DATABASE_URL=postgresql://[user]:[pass]@[host]:[port]/[db]
PYTHONUNBUFFERED=1
```

**Nota:** Render puede proporcionar PostgreSQL automáticamente. Consulta `docs/DEPLOYMENT.md` para más detalles.

### Frontend

```
VITE_API_URL=https://laliga-predictor-api.onrender.com
```

---

## 🎯 Checklist de Validación

Antes de considerar el deploy como completado:

- [ ] Commit 1-7 están en GitHub rama `develop`
- [ ] Backend desplegado en Render (Web Service)
- [ ] Frontend desplegado en Render (Static Site)
- [ ] `/health` endpoint responde con modelos cargados
- [ ] `/teams` endpoint retorna 20 equipos
- [ ] Frontend carga sin errores
- [ ] Puedo seleccionar equipos en el formulario
- [ ] Puedo hacer una predicción y ver resultados
- [ ] Las 3 predicciones se muestran correctamente

---

## 📊 URLs de Producción (Después del Deploy)

```
Backend API:  https://laliga-predictor-api.onrender.com
Frontend:     https://laliga-predictor-web.onrender.com
```

---

## 🆘 Si Algo Falla

1. **Backend no inicia:**
   - Revisa logs en Render Dashboard
   - Verifica variables de entorno
   - Comprueba que Dockerfile está correcto

2. **Frontend no conecta API:**
   - Verifica `VITE_API_URL` está correcto
   - Comprueba CORS en backend
   - Abre browser DevTools (F12) → Console

3. **Modelos no cargados:**
   - Verifica `/health` endpoint
   - Los archivos `.joblib` deben estar en `backend/models/`
   - Puede necesitar reentrenamiento

**Solución:** Lee `docs/DEPLOYMENT.md` sección "Troubleshooting"

---

## 📝 Resumen

| Tarea | Status | URL |
|-------|--------|-----|
| 7 commits listos | ✅ | rama develop |
| Documentación completa | ✅ | `/docs/` |
| Backend a desplegar | ⏳ | render.com |
| Frontend a desplegar | ⏳ | render.com |
| Test E2E | ⏳ | https://...onrender.com |

**Progreso:** 70% → 100% (al completar steps 1-5)

---

## 🎓 Próximas Mejoras (Opcional)

Después de que todo funcione en Render:

1. **CI/CD Avanzado:** GitHub Actions → Build → Push a Docker Registry → Deploy
2. **Database Persistente:** Migrar a Neon o Supabase
3. **Monitoreo:** Sentry, DataDog, CloudFlare CDN
4. **Analytics:** Tracking de predicciones exitosas
5. **Modelo Actualizado:** Reentrenamiento semanal automático

---

**¡Estamos al final! 🎉 Solo necesitas hacer 5 pasos sencillos.**

Cuando termines, avisame y pasamos al BONUS Phase (documentación final).

---

**Referencia:**
- GitHub: https://github.com/nicorg5/Proyecto_ML_Pred_Ganador
- Render: https://render.com/
- Documentación: Ver `/docs/DEPLOYMENT.md` y `/docs/API.md`
