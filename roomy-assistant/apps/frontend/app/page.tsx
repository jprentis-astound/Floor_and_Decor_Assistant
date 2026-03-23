import dynamic from "next/dynamic";

// Prevent SSR — CopilotKit hooks require client-side context
const RoomyApp = dynamic(() => import("@/components/RoomyApp"), { ssr: false });

export default function Page() {
  return <RoomyApp />;
}
