import React from 'react';

interface LogoProps {
  className?: string;
}

export const Logo: React.FC<LogoProps> = ({ className = 'w-full h-full' }) => {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#d8b4fe" /> {/* purple-300 */}
          <stop offset="50%" stopColor="#a78bfa" /> {/* violet-400 */}
          <stop offset="100%" stopColor="#6366f1" /> {/* indigo-500 */}
        </linearGradient>
      </defs>
      
      {/* Outer circular network/fintech orbit */}
      <circle cx="12" cy="12" r="9" stroke="url(#logo-grad)" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.6" />
      
      {/* Connected nodes */}
      <circle cx="12" cy="3" r="1.5" fill="#a78bfa" />
      <circle cx="21" cy="12" r="1.5" fill="#6366f1" />
      <circle cx="12" cy="21" r="1.5" fill="#a78bfa" />
      <circle cx="3" cy="12" r="1.5" fill="#6366f1" />

      {/* Main AI sparkle logo inside */}
      <path
        d="M12 6C11.2 9 9 11.2 6 12C9 12.8 11.2 15 12 18C12.8 15 15 12.8 18 12C15 11.2 12.8 9 12 6Z"
        fill="url(#logo-grad)"
      />
      {/* Inner glowing core */}
      <path
        d="M12 9C11.6 10.5 10.5 11.6 9 12C10.5 12.4 11.6 13.5 12 15C12.4 13.5 13.5 12.4 15 12C13.5 11.6 12.4 10.5 12 9Z"
        fill="#FFFFFF"
        opacity="0.9"
      />
    </svg>
  );
};

export default Logo;
