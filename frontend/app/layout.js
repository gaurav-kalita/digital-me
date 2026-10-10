// frontend/app/layout.js

import "./globals.css";

export const metadata = {
  title: "Digital Me",
  description: "A simple chat interface for the Digital Me AI service.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
