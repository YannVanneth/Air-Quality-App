import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import RootLayout from './layouts/RootLayout.jsx'
import AirQuality from './pages/AirQuality.jsx'
import About from './pages/About.jsx'
import Home from './pages/Home.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path='/' element={<RootLayout />}>
          <Route index element={<App />} />
          <Route path='/about' element={<About/>} />
          <Route path='/air_quality' element={<AirQuality />} />
          {/* <Route path='/Homepage' element = {<Home/>} /> */}

        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
