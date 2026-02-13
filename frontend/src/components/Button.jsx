import React from 'react';

const Button = ({ 
  loading = false, 
  disabled = false, 
  variant = '', 
  className = '', 
  children, 
  ...props 
}) => {
  // Combine variant and custom classes
  const combinedClassName = `${variant} ${className} ${loading ? 'loading' : ''}`.trim();

  return (
    <button 
      className={combinedClassName} 
      disabled={disabled || loading} 
      {...props}
    >
      {loading && (
        <span className="spinner-wrapper">
          <svg className="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <circle className="spinner-bg" cx="12" cy="12" r="10"></circle>
            <path className="spinner-fg" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </span>
      )}
      <span style={{ display: 'contents', visibility: loading ? 'hidden' : 'visible' }}>
        {children}
      </span>
    </button>
  );
};

export default Button;
