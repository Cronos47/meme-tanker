import "./globals.css";

export const metadata = { title: "MemeForge Studio", description: "Instant memes & short videos" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
