import { useState } from 'react'
import './PredictionForm.css'

function PredictionForm({ teams, onSubmit, loading }) {
  const [formData, setFormData] = useState({
    homeTeam: '',
    awayTeam: '',
    matchDate: new Date().toISOString().split('T')[0],
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (formData.homeTeam && formData.awayTeam && formData.matchDate) {
      onSubmit(formData)
    }
  }

  const getMinDate = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

  return (
    <form className="prediction-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="homeTeam">Home Team</label>
        <select
          id="homeTeam"
          name="homeTeam"
          value={formData.homeTeam}
          onChange={handleChange}
          disabled={loading}
          required
        >
          <option value="">Select home team</option>
          {teams.map((team) => (
            <option key={team} value={team}>
              {team}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="awayTeam">Away Team</label>
        <select
          id="awayTeam"
          name="awayTeam"
          value={formData.awayTeam}
          onChange={handleChange}
          disabled={loading}
          required
        >
          <option value="">Select away team</option>
          {teams.map((team) => (
            <option key={team} value={team}>
              {team}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="matchDate">Match Date</label>
        <input
          id="matchDate"
          type="date"
          name="matchDate"
          value={formData.matchDate}
          onChange={handleChange}
          min={getMinDate()}
          disabled={loading}
          required
        />
      </div>

      <button
        type="submit"
        className="btn-primary submit-button"
        disabled={loading || !formData.homeTeam || !formData.awayTeam}
      >
        {loading ? 'Predicting...' : 'Get Prediction'}
      </button>
    </form>
  )
}

export default PredictionForm
