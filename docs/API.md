# 📡 API Documentation - LaLiga Predictor

**Base URL (Local):** `http://localhost:8000`  
**Base URL (Producción):** `https://laliga-predictor-api.onrender.com`  
**Version:** 2.0.0  
**Última actualización:** 15 de mayo, 2026

---

## 📚 Tabla de Contenidos

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Response Schemas](#response-schemas)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

---

## 🎯 Overview

LaLiga Predictor API proporciona predicciones ML para partidos de La Liga Española.

**Tres tipos de predicciones por partido:**
- **Winner:** Probabilidad de victoria Local (H), Empate (D), Victoria Visitante (A)
- **Goals O/U:** Probabilidad de Over/Under para 1.5, 2.5, 3.5 goles
- **Cards O/U:** Probabilidad de Over/Under para 3.5, 4.5, 5.5 tarjetas

---

## 🔐 Authentication

**Tipo:** Ninguno (API pública)

CORS está habilitado. El API acepta requests desde cualquier origen.

---

## 🔗 Endpoints

### 1. GET `/`

**Descripción:** Información del API

**Request:**
```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "name": "LaLiga Predictor API",
  "version": "2.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

**Status Code:** `200 OK`

---

### 2. GET `/health`

**Descripción:** Health check del servicio y estado de modelos

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": {
    "winner": true,
    "goals_ou": 3,
    "cards_ou": 3
  },
  "timestamp": "2026-05-15T16:00:00.123456"
}
```

**Status Code:** 
- `200 OK` - Servicio saludable, modelos cargados
- `503 Service Unavailable` - Modelos no disponibles

**Campos:**
- `status` (string): Estado del servicio ("healthy", "unhealthy")
- `models_loaded` (dict):
  - `winner` (bool): Si el modelo de ganador está cargado
  - `goals_ou` (int): Cantidad de modelos Goals O/U cargados (0-3)
  - `cards_ou` (int): Cantidad de modelos Cards O/U cargados (0-3)
- `timestamp` (ISO 8601): Timestamp de la respuesta

---

### 3. GET `/teams`

**Descripción:** Lista de 20 equipos de La Liga 2025/26

**Request:**
```bash
curl http://localhost:8000/teams
```

**Response:**
```json
{
  "teams": [
    "Alavés",
    "Athletic Club",
    "Atlético Madrid",
    "Barcelona",
    "Celta Vigo",
    "Elche CF",
    "Espanyol",
    "Getafe",
    "Girona",
    "Levante UD",
    "Mallorca",
    "Osasuna",
    "Rayo Vallecano",
    "Real Betis",
    "Real Madrid",
    "Real Oviedo",
    "Real Sociedad",
    "Sevilla",
    "Valencia",
    "Villarreal"
  ],
  "count": 20
}
```

**Status Code:** `200 OK`

**Campos:**
- `teams` (list[string]): Array de nombres de equipos, ordenados alfabéticamente
- `count` (int): Total de equipos (siempre 20)

---

### 4. POST `/predict`

**Descripción:** Obtener predicción de un partido

**Request:**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "home_team": "Real Madrid",
    "away_team": "Barcelona",
    "match_date": "2026-05-20"
  }'
```

**Request Body:**
```json
{
  "home_team": "Real Madrid",
  "away_team": "Barcelona",
  "match_date": "2026-05-20"
}
```

**Validaciones:**
- `home_team` (string, required): Nombre exacto del equipo (de `/teams`)
- `away_team` (string, required): Nombre exacto del equipo (de `/teams`)
- `match_date` (string, required): Formato ISO 8601 (YYYY-MM-DD)

**Response:**
```json
{
  "home_team": "Real Madrid",
  "away_team": "Barcelona",
  "match_date": "2026-05-20",
  "winner": {
    "predicted": "H",
    "home_prob": 0.45,
    "draw_prob": 0.30,
    "away_prob": 0.25
  },
  "goals": {
    "1.5": {
      "over": 0.80,
      "under": 0.20
    },
    "2.5": {
      "over": 0.60,
      "under": 0.40
    },
    "3.5": {
      "over": 0.35,
      "under": 0.65
    }
  },
  "cards": {
    "3.5": {
      "over": 0.70,
      "under": 0.30
    },
    "4.5": {
      "over": 0.55,
      "under": 0.45
    },
    "5.5": {
      "over": 0.25,
      "under": 0.75
    }
  },
  "model_version": "v2.0",
  "generated_at": "2026-05-15T16:00:00.123456"
}
```

**Status Code:**
- `200 OK` - Predicción exitosa
- `400 Bad Request` - Equipos inválidos, formato de fecha incorrecto
- `503 Service Unavailable` - Modelos no están cargados

**Campos Response:**
- `home_team` (string): Nombre del equipo local (eco del request)
- `away_team` (string): Nombre del equipo visitante (eco del request)
- `match_date` (string): Fecha del partido (eco del request)
- `winner` (object): Predicción de ganador
  - `predicted` (string): Predicción final ("H", "D", "A")
  - `home_prob` (float): Probabilidad Local [0-1]
  - `draw_prob` (float): Probabilidad Empate [0-1]
  - `away_prob` (float): Probabilidad Visitante [0-1]
- `goals` (dict): Predicción Goals Over/Under
  - Claves: "1.5", "2.5", "3.5"
  - Valores: {over: float, under: float}
- `cards` (dict): Predicción Cards Over/Under
  - Claves: "3.5", "4.5", "5.5"
  - Valores: {over: float, under: float}
- `model_version` (string): Versión del modelo usado
- `generated_at` (ISO 8601): Timestamp de generación

---

### 5. GET `/docs`

**Descripción:** Swagger UI interactiva (auto-generada por FastAPI)

**URL:**
```
http://localhost:8000/docs
```

Permite:
- Ver todos los endpoints en formato visual
- Probar endpoints directamente
- Ver esquemas de request/response
- Descargar OpenAPI JSON

---

## 📦 Response Schemas

### PredictionRequest

```typescript
{
  home_team: string;      // Nombre del equipo local
  away_team: string;      // Nombre del equipo visitante
  match_date: string;     // YYYY-MM-DD
}
```

### PredictionResponse

```typescript
{
  home_team: string;
  away_team: string;
  match_date: string;
  winner: {
    predicted: "H" | "D" | "A";
    home_prob: number;      // [0, 1]
    draw_prob: number;      // [0, 1]
    away_prob: number;      // [0, 1]
  };
  goals: {
    "1.5": { over: number; under: number };
    "2.5": { over: number; under: number };
    "3.5": { over: number; under: number };
  };
  cards: {
    "3.5": { over: number; under: number };
    "4.5": { over: number; under: number };
    "5.5": { over: number; under: number };
  };
  model_version: string;
  generated_at: string;    // ISO 8601 timestamp
}
```

### HealthResponse

```typescript
{
  status: "healthy" | "unhealthy";
  models_loaded: {
    winner: boolean;
    goals_ou: number;    // 0-3
    cards_ou: number;    // 0-3
  };
  timestamp: string;     // ISO 8601
}
```

### TeamsResponse

```typescript
{
  teams: string[];       // 20 equipos, ordenados alfabéticamente
  count: number;         // 20
}
```

---

## ⚠️ Error Handling

### Códigos de Error

```json
{
  "detail": "string - descripción del error"
}
```

### Ejemplos de Errores

**400 Bad Request:**
```json
{
  "detail": "Invalid team name: 'Real Madri'. Check /teams for valid names."
}
```

**503 Service Unavailable:**
```json
{
  "detail": "Winner model not loaded. Models may not be trained yet."
}
```

### Manejo en Cliente

```javascript
try {
  const response = await fetch('http://localhost:8000/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      home_team: "Real Madrid",
      away_team: "Barcelona",
      match_date: "2026-05-20"
    })
  });

  if (!response.ok) {
    const error = await response.json();
    console.error(`Error ${response.status}: ${error.detail}`);
  } else {
    const prediction = await response.json();
    console.log(prediction);
  }
} catch (error) {
  console.error('Network error:', error);
}
```

---

## 📋 Examples

### Python con `requests`

```python
import requests
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

# 1. Health Check
response = requests.get(f"{API_URL}/health")
print(response.json())

# 2. Obtener Equipos
response = requests.get(f"{API_URL}/teams")
teams = response.json()["teams"]
print(f"Disponibles: {teams}")

# 3. Hacer Predicción
prediction_data = {
    "home_team": "Real Madrid",
    "away_team": "Barcelona",
    "match_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
}

response = requests.post(
    f"{API_URL}/predict",
    json=prediction_data
)

if response.status_code == 200:
    prediction = response.json()
    
    # Winner
    print(f"🏆 Winner: {prediction['winner']['predicted']}")
    print(f"  Home: {prediction['winner']['home_prob']:.1%}")
    print(f"  Draw: {prediction['winner']['draw_prob']:.1%}")
    print(f"  Away: {prediction['winner']['away_prob']:.1%}")
    
    # Goals
    print("\n⚽ Goals:")
    for line, probs in prediction['goals'].items():
        print(f"  {line}: Over {probs['over']:.1%} / Under {probs['under']:.1%}")
    
    # Cards
    print("\n🟡 Cards:")
    for line, probs in prediction['cards'].items():
        print(f"  {line}: Over {probs['over']:.1%} / Under {probs['under']:.1%}")
else:
    print(f"Error {response.status_code}: {response.json()['detail']}")
```

### JavaScript / Fetch

```javascript
const API_URL = "http://localhost:8000";

// 1. Health Check
fetch(`${API_URL}/health`)
  .then(r => r.json())
  .then(data => console.log("API Status:", data.status));

// 2. Get Teams
fetch(`${API_URL}/teams`)
  .then(r => r.json())
  .then(data => console.log("Available teams:", data.teams));

// 3. Make Prediction
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
const matchDate = tomorrow.toISOString().split('T')[0];

fetch(`${API_URL}/predict`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    home_team: "Real Madrid",
    away_team: "Barcelona",
    match_date: matchDate
  })
})
  .then(r => r.json())
  .then(prediction => {
    console.log("🏆 Winner:", prediction.winner);
    console.log("⚽ Goals:", prediction.goals);
    console.log("🟡 Cards:", prediction.cards);
  });
```

### cURL

```bash
# 1. Health
curl http://localhost:8000/health

# 2. Teams
curl http://localhost:8000/teams

# 3. Predicción
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "home_team": "Real Madrid",
    "away_team": "Barcelona",
    "match_date": "2026-05-20"
  }' | python -m json.tool
```

---

## 🔄 Rate Limiting

**Actual:** Sin limitación

En producción (Render), se recomienda:
- Máximo 100 requests/minuto por IP
- Máximo 10 requests/segundo por IP

---

## 🔒 CORS

CORS está habilitado para todos los orígenes:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

---

## 📊 Performance

**Latencia típica:**
- Health check: < 100ms
- Teams list: < 100ms
- Prediction: 200-500ms (incluye feature engineering)

**Recomendaciones:**
- Cachea la lista de equipos (`/teams`)
- No hagas requests de predicción más de 1x/segundo por usuario
- Usa health check cada 5 minutos para monitoreo

---

## 🚀 Versionado

**Versión Actual:** 2.0.0

Cambios futuros se documentarán acá.

---

## 📞 Support

Para reportar bugs o sugerir mejoras:
1. Abre un issue en GitHub
2. Contacta al equipo de desarrollo
3. Revisa los logs en `/health` para diagnosticar

---

**¡API Lista para Producción! 🎯**
