import './HistoryPage.css'

function HistoryPage() {
  return (
    <div className="history-page">
      <div className="history-container">
        <div className="card">
          <h2>🔮 Prediction History</h2>
          <p className="coming-soon">
            Coming soon! This feature will show your prediction history and accuracy tracking.
          </p>
          <div className="feature-list">
            <h3>Planned Features:</h3>
            <ul>
              <li>✓ View all your past predictions</li>
              <li>✓ Track prediction accuracy</li>
              <li>✓ Compare predicted vs actual results</li>
              <li>✓ Export prediction history</li>
              <li>✓ Analytics and statistics</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HistoryPage
