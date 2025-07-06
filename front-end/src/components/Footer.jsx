import "../css/Footer.css"
import logo from '../assets/icons/logo.png'; // replace with your actual logo path

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">

        <div className="footer-column">
          <div className="footer-logo">
            <img src={logo} alt="Air Pollution Logo" />
            <h3>Air Pollution</h3>
          </div>
          <p>Lorem ipsum dolor sit amet consectetur adipiscing elit aliquam</p>
          <div className="footer-socials">
            <i className="fab fa-facebook-f" />
            <i className="fab fa-twitter" />
            <i className="fab fa-instagram" />
            <i className="fab fa-linkedin-in" />
            <i className="fab fa-youtube" />
          </div>
        </div>

        <div className="footer-column">
          <h4>Live Air Quality</h4>
          <ul>
            <li>Features</li>
            <li>Pricing</li>
            <li>Case studies</li>
            <li>Reviews</li>
            <li>Updates</li>
          </ul>
        </div>

        <div className="footer-column">
          <h4>Reports & Analytics</h4>
          <ul>
            <li>About</li>
            <li>Contact us</li>
            <li>Careers</li>
            <li>Culture</li>
            <li>Blog</li>
          </ul>
        </div>

        <div className="footer-column">
          <h4>Contacts</h4>
          <ul className="footer-contacts">
            <li><i className="fas fa-envelope" /> contact@company.com</li>
            <li><i className="fas fa-phone" /> (+855) 123-456-78</li>
            <li><i className="fas fa-map-marker-alt" /> 794 Mcallister St<br />San Francisco, 94102</li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <span>Copyright © 2022 BRIX Templates</span>
        <div>
          <a href="#" style={{color:"white"}}>All Rights Reserved</a> | <a href="#">Terms and Conditions</a> | <a href="#">Privacy Policy</a>
        </div>
      </div>
    </footer>
  );
}
