import type { Metadata } from 'next'
import './globals.css'

// No Google Fonts — the Docker build environment has no internet access.
// Tailwind's 'font-sans' uses the OS system font stack:
// -apple-system, BlinkMacSystemFont, "Segoe UI", etc.
// These are already installed on every device, so there's zero network cost.

export const metadata: Metadata = {
  title: 'Task Management',
  description: 'Team task management',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  )
}
