import { useState, useEffect } from 'react'
import api from '../services/api'
import PredictionForm from '../components/PredictionForm'
import PredictionResult from '../components/PredictionResult'
import './PredictorPage.css'

function PredictorPage() {
  const [teams, setTeams] = useState([])
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const response = await api.getTeams()
        setTeams(response.data.teams)
      } catch (err) {
        console.error('Failed to fetch teams:', err)
        setError('Failed to load teams. Please check API connection.')
      }
    }

    fetchTeams()
  }, [])

  const handlePredict = async (formData) => {
    setLoading(true)
    setError(null)
    setPrediction(null)

    try {
      const response = await api.predictMatch(
        formData.homeTeam,
        formData.awayTeam,
        formData.matchDate
      )
      setPrediction(response.data)
    } catch (err) {
      console.error('Prediction failed:', err)
      setError(
        err.response?.data?.detail ||
        'Failed to get prediction. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="predictor-page">
      <div className="predictor-container">
        <div className="predictor-form-section">
          <h2>Match Prediction</h2>
          {error && <div className="alert alert-error">{error}</div>}
          <PredictionForm teams={teams} onSubmit={handlePredict} loading={loading} />
        </div>

        {prediction && (
          <div className="predictor-result-section">
            <h2>Prediction Result</h2>
            <PredictionResult prediction={prediction} />
          </div>
        )}

        {loading && (
          <div className="predictor-result-section">
            <div className="loading-container">
              <div className="loading"></div>
              <p>Generating prediction...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default PredictorPage
