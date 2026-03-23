import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

export const metadata = {
  title: "Roomy — Floor & Decor Assistant",
  description: "AI-powered tile search assistant for Floor & Decor",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          agent="roomy_assistant"
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
