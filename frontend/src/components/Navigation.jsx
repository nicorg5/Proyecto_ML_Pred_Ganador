import './Navigation.css'

function Navigation({ currentPage, setCurrentPage }) {
  return (
    <nav className="navigation">
      <div className="nav-container">
        <button
          className={`nav-button ${currentPage === 'predictor' ? 'active' : ''}`}
          onClick={() => setCurrentPage('predictor')}
        >
          🎯 Predictor
        </button>
        <button
          className={`nav-button ${currentPage === 'history' ? 'active' : ''}`}
          onClick={() => setCurrentPage('history')}
        >
          📊 History
        </button>
      </div>
    </nav>
  )
}

export default Navigation
