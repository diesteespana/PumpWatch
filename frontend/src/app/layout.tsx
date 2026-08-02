import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: { default: "PumpWatch", template: "%s | PumpWatch" },
  description: "Real-time on-chain intelligence. Track whales, follow smart money.",
  metadataBase: new URL("https://pumpwat.ch"),
  openGraph: {
    siteName: "PumpWatch",
    url: "https://pumpwat.ch",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#00E5FF",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans bg-surface text-white antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
