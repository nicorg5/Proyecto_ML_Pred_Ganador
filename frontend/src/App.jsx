import { useState, useEffect } from 'react'
import Header from './components/Header'
import Navigation from './components/Navigation'
import PredictorPage from './pages/PredictorPage'
import HistoryPage from './pages/HistoryPage'
import api from './services/api'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('predictor')
  const [apiHealth, setApiHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await api.health()
        setApiHealth(response.data)
      } catch (error) {
        console.error('API health check failed:', error)
        setApiHealth(null)
      } finally {
        setLoading(false)
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Check every 30 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <>
      <Header apiStatus={apiHealth?.status} loading={loading} />
      <Navigation currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <main>
        {currentPage === 'predictor' && <PredictorPage />}
        {currentPage === 'history' && <HistoryPage />}
      </main>
    </>
  )
}

export default App
