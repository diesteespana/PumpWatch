"use client";

import { useState } from "react";
import Link from "next/link";
import type { Metadata } from "next";
import { useLogin } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-6">
      <h1 className="mb-1 text-xl font-bold text-white">Sign in</h1>
      <p className="mb-6 text-sm text-white/40">
        Monitor on-chain activity in real time.
      </p>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <Input
          label="Password"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
        <Button type="submit" loading={login.isPending} size="lg" className="mt-1 w-full">
          Sign in
        </Button>
      </form>

      <p className="mt-5 text-center text-xs text-white/40">
        No account?{" "}
        <Link href="/register" className="text-brand hover:underline">
          Create one
        </Link>
      </p>
    </div>
  );
}
