import './PredictionResult.css'

function PredictionResult({ prediction }) {
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const getProbabilityColor = (probability) => {
    if (probability > 0.5) return 'high'
    if (probability > 0.35) return 'medium'
    return 'low'
  }

  return (
    <div className="prediction-result">
      <div className="match-info">
        <div className="match-date">
          📅 {formatDate(prediction.match_date)}
        </div>
        <div className="match-teams">
          <span className="team">{prediction.home_team}</span>
          <span className="vs">vs</span>
          <span className="team">{prediction.away_team}</span>
        </div>
      </div>

      <div className="prediction-section">
        <h3>🏆 Winner</h3>
        <div className="winner-predictions">
          <div className={`prob-item ${getProbabilityColor(prediction.winner.home_prob)}`}>
            <span className="team-name">{prediction.home_team}</span>
            <span className="probability">{(prediction.winner.home_prob * 100).toFixed(1)}%</span>
          </div>
          <div className={`prob-item ${getProbabilityColor(prediction.winner.draw_prob)}`}>
            <span className="team-name">Draw</span>
            <span className="probability">{(prediction.winner.draw_prob * 100).toFixed(1)}%</span>
          </div>
          <div className={`prob-item ${getProbabilityColor(prediction.winner.away_prob)}`}>
            <span className="team-name">{prediction.away_team}</span>
            <span className="probability">{(prediction.winner.away_prob * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>

      <div className="prediction-section">
        <h3>⚽ Goals</h3>
        <div className="ou-predictions">
          {Object.entries(prediction.goals).map(([line, probs]) => (
            <div key={line} className="ou-item">
              <span className="line-label">{line} Goals</span>
              <div className="ou-probs">
                <div className={`prob-badge over`}>
                  Over: {(probs.over * 100).toFixed(1)}%
                </div>
                <div className={`prob-badge under`}>
                  Under: {(probs.under * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="prediction-section">
        <h3>🟡 Cards</h3>
        <div className="ou-predictions">
          {Object.entries(prediction.cards).map(([line, probs]) => (
            <div key={line} className="ou-item">
              <span className="line-label">{line} Cards</span>
              <div className="ou-probs">
                <div className={`prob-badge over`}>
                  Over: {(probs.over * 100).toFixed(1)}%
                </div>
                <div className={`prob-badge under`}>
                  Under: {(probs.under * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="model-info">
        <small>
          Model v{prediction.model_version} • Generated: {new Date(prediction.generated_at).toLocaleTimeString()}
        </small>
      </div>
    </div>
  )
}

export default PredictionResult
