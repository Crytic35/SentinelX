import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SentinelX — Zero-Trust Security for AI Payment Agents",
  description: "AI agents can spend money. SentinelX makes sure they don't spend yours. PayPal AI Hackathon 2026.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#080b11] text-slate-100 antialiased selection:bg-brand-blue selection:text-white">
        {children}
      </body>
    </html>
  );
}

