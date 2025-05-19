import "../css/ComingSoon.css"
import React, { useState, useEffect } from 'react';
const ComingSoon = () => {
  const fullText = 'Coming Soon...';
  const [displayedText, setDisplayedText] = useState('');
  const [index, setIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(true);

  useEffect(() => {
    const speed = isDeleting ? 80 : 150;

    const timer = setTimeout(() => {
      setDisplayedText(fullText.slice(0, index));

      if (!isDeleting && index < fullText.length) {
        setIndex((prev) => prev + 1);
      } else if (isDeleting && index > 0) {
        setIndex((prev) => prev - 1);
      } else {
        setIsDeleting(!isDeleting);
      }
    }, speed);

    return () => clearTimeout(timer);
  }, [index, isDeleting]);

  return (
    <div className="coming-soon">
      <div style={{ textAlign: 'center', marginTop: '100px', fontSize: '36px', color: 'black', fontWeight: 'bold' }}>
      {displayedText}
      <span className="cursor">|</span>
    </div>
    </div>
    
  );
};
export default ComingSoon;
