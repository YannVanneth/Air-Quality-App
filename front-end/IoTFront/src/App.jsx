import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";

function App() {
  const [count, setCount] = useState(0);

  return (
    <>
      <section class='contents'>
        <h1 className="ml-9">Why We Make Air Pollution?</h1>
        <div className="content-area">
          <div class='col-6'>
            <div className="item">
               <h4>Phnom Penh Fire and Smoke Map</h4>
          <p>
            This map relies on data provided from a number of sources, including
            AirNow, the Western Regional Climate Center, AirSis, and PurpleAir
            for monitoring and sensor data, and the NOAA Hazard Mapping System
            and National Interagency Fire Center for fire and smoke plume
            information.
          </p>
            <button class="btn">Read More</button>
          </div>
        </div>
        <div class='col-6'>
          <div class="item">
            <img src="src/image/image (1).png" alt="" />
          </div>
        </div>
        <div class='col-6'>
          <div class="item">
            <img src="src/image/image (2).png" alt="" />
          </div>
        </div>
         <div class='col-6'>
            <div className="item">
               <h4>Phnom Penh Fire and Smoke Map</h4>
          <p>
            This map relies on data provided from a number of sources, including
            AirNow, the Western Regional Climate Center, AirSis, and PurpleAir
            for monitoring and sensor data, and the NOAA Hazard Mapping System
            and National Interagency Fire Center for fire and smoke plume
            information.
          </p>
            <button class="btn">Read More</button>
          </div>
        </div>
        <div class='col-6'>
            <div className="item">
               <h4>Phnom Penh Fire and Smoke Map</h4>
          <p>
            This map relies on data provided from a number of sources, including
            AirNow, the Western Regional Climate Center, AirSis, and PurpleAir
            for monitoring and sensor data, and the NOAA Hazard Mapping System
            and National Interagency Fire Center for fire and smoke plume
            information.
          </p>
            <button class="btn">Read More</button>
          </div>
        </div>
        <div class='col-6'>
          <div class="item">
            <img src="src/image/image (3).png" alt="" />
          </div>
        </div>
        
        </div>
      </section>
    </>
  );
}

export default App;
