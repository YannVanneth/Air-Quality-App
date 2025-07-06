import "./App.css";
import Footer from "./components/Footer";
import Header from "./components/Header";
import HealthAdvice from "./pages/HealthAdvice";
import AirQuality from "./pages/AirQuality"
import AboutUs from "./pages/AboutUs"
import ReportsAnalytics from "./pages/ReportsAnalytics"
import Home from "./pages/Home";

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from "./layout/layout";


function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/air_quality" element={<AirQuality />} />
          <Route path="/report_analytics" element={<ReportsAnalytics />} />
          <Route path="/health_advice" element={<HealthAdvice />} />
          <Route path="/about_us" element={<AboutUs />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
