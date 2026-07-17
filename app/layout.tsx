import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Academic & Research Assistant | Qdrant RAG",
  description:
    "AI-powered research assistant with Qdrant vector search. Upload any PDF and get grounded, citation-backed answers from your academic documents.",
  keywords: ["RAG", "Qdrant", "research assistant", "academic AI", "PDF analysis"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* Google Fonts: Inter (UI) + JetBrains Mono (code/citations) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
