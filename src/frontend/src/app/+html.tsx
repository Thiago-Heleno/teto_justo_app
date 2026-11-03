import type { PropsWithChildren } from "react";

export default function Document({ children }: PropsWithChildren) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#f4f0e8" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <link rel="apple-touch-icon" href="/assets/images/icon.png" />
      </head>
      <body>{children}</body>
    </html>
  );
}
