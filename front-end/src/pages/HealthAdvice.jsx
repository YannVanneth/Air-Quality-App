import "../css/HealthAdvice.css";
import image_1 from "../assets/images/image_1.png";
import image_2 from "../assets/images/image_2.png";
import image_3 from "../assets/images/image_3.png";
function HealthAdvice() {
  return (
    <>
      <div className="container body">
        <div className="row part-1">
          <div className="col-1">
            <h1>What are the effects of air pollution on human health?</h1>
            <p>
              Both short- and long-term exposure to air pollution can lead to a
              wide range of diseases, including stroke, chronic obstructive
              pulmonary disease, trachea, bronchus and lung cancers, aggravated
              asthma and lower respiratory infections
            </p>
          </div>
          <div className="col-2">
            <img src={image_1} alt="" />
          </div>
        </div>
        <div className="row part-2">
          <div className="col-1">
            <img src={image_2} alt="" />
          </div>
          <div className="col-2">
            <h1>How air pollution is destroying our health</h1>
            <p>
              There are two main types of air pollution: ambient air pollution
              (outdoor pollution) and household air pollution (indoor air
              pollution). Ambient air pollution is a major environmental health
              problem affecting everyone in low-, middle-, and high-income
              countries as its source – combustion of fossil fuel – is
              ubiquitous. Household air pollution is mainly caused by the use of
              solid fuels (such as wood, crop wastes, charcoal, coal and dung)
              and kerosene in open fires and inefficient stoves.
            </p>
          </div>
        </div>
        <div className="row part-3">
          <div className="col-1">
            <h1>
              There are ways to prevent, control and eventually reduce air
              pollution:
            </h1>
            <ol>
              <li>
                Renewable fuel and clean energy production: the most basic
                solution for air pollution is to move away from fossil fuels,
                replacing them with alternative energies like solar, wind and
                geothermal.
              </li>
              <li>Energy conservation and efficiency: producing clean energy is crucial. But equally important is to reduce our consumption of energy by adopting responsible habits and using more efficient devices.</li>
              <li>Eco-friendly transportation: shifting to electric vehicles and hydrogen vehicles, and promoting shared mobility (i.e carpooling, and public transports) could reduce air pollution.</li>
              <li>Green building: from planning to demolition, green building aims to create environmentally responsible and resource-efficient structures to reduce their carbon footprint</li>
            </ol>
          </div>
          <div className="col-2">
            <img src={image_3} alt="" />
          </div>
        </div>
      </div>
    </>
  );
}
export default HealthAdvice;
