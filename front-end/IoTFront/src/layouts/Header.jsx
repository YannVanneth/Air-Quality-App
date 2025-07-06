import React from "react";
import "../css/Header.css";
import { Link } from "react-router-dom";
import logo from "../assets/icons/logo.png";
function Header() {
  return (
    <>
      <header className="navbar">
        <div className="container">
          <Link to={"/"} className="logo">
            <img src={logo} alt="Air Pollution Logo" />
            <span>Air Pollution</span>
          </Link>
          <ul className="nav-links">
            <li>
              <Link to={"/air_quality"}>Air Quality</Link>
            </li>
            <li>
              <Link to={"/about"}>About Us</Link>
            </li>
          </ul>
          <a href="" className="btn">
            Get started
          </a>
        </div>
      </header>
    </>
  );
}
export default Header;
