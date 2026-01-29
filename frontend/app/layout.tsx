import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "IRONMIND - Technical Document Intelligence",
  description: "AI-powered analysis for aerospace & defense technical documents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <header className="fixed top-0 w-full bg-white border-b z-50 shadow-sm">
          <div className="container mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/IAI_logo_2025.jpg" alt="IAI Logo" className="h-10 w-auto" />
              <span className="text-xl font-bold text-gray-900">IRONMIND</span>
            </div>
            <nav className="flex items-center gap-4">
              <a href="/dashboard" className="text-gray-700 hover:text-gray-900">
                Dashboard
              </a>
              <a href="/login" className="text-gray-700 hover:text-gray-900">
                Login
              </a>
            </nav>
          </div>
        </header>
        <main className="pt-16 min-h-screen">{children}</main>
        <footer className="bg-gray-50 border-t py-4">
          <div className="container mx-auto px-4 text-center text-gray-600 text-sm">
            IRONMIND POC - Israel Aerospace Industries
          </div>
        </footer>
      </body>
    </html>
  );
}
