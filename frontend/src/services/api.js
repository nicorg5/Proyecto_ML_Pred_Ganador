import axios from 'axios'

const API_BASE_URL = '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  // Health check
  health: () => apiClient.get('/health'),

  // Get available teams
  getTeams: () => apiClient.get('/teams'),

  // Get match prediction
  predictMatch: (homeTeam, awayTeam, matchDate) =>
    apiClient.post('/predict', {
      home_team: homeTeam,
      away_team: awayTeam,
      match_date: matchDate,
    }),

  // Get API info
  getInfo: () => apiClient.get('/'),
}

export default api
