import type { ReactNode } from "react";
import { Activity } from "lucide-react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="mb-8 flex items-center gap-2.5">
        <Activity className="h-6 w-6 text-brand" />
        <span className="text-lg font-bold tracking-wide text-white">
          PUMP<span className="text-brand">WATCH</span>
        </span>
      </div>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  );
}
