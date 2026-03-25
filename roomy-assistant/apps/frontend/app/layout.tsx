import "./globals.css";

export const metadata = {
  title: "Help Center — Floor & Decor",
  description:
    "Get help with flooring, installation, orders, and more from Roomy, your Floor & Decor assistant.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
