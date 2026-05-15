import './Header.css'

function Header({ apiStatus, loading }) {
  return (
    <header className="header">
      <div className="header-container">
        <div className="header-title">
          <h1>⚽ LaLiga Predictor</h1>
          <p>Machine Learning predictions for La Liga matches</p>
        </div>
        <div className="header-status">
          {loading ? (
            <div className="status-badge loading">
              Checking API...
            </div>
          ) : (
            <div className={`status-badge ${apiStatus === 'healthy' ? 'healthy' : 'offline'}`}>
              {apiStatus === 'healthy' ? '✓ API Ready' : '✗ API Offline'}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
