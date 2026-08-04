"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { queryClient } from "@/lib/queryClient";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#161B22",
            color: "#fff",
            border: "1px solid #30363D",
            fontSize: "13px",
          },
          success: { iconTheme: { primary: "#00C853", secondary: "#fff" } },
          error: { iconTheme: { primary: "#FF3D00", secondary: "#fff" } },
        }}
      />
    </QueryClientProvider>
  );
}
