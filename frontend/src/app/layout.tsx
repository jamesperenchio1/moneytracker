import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MoneyTracker — Smart Finance Dashboard",
  description: "Track investments, banking, and spending across Thai banks and global brokerages",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
