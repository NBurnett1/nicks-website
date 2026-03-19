import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import StockDetail from './pages/StockDetail'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/stock/:ticker" element={<StockDetail />} />
    </Routes>
  )
}
