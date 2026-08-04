"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRegister, useLogin } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const register = useRegister();
  const login = useLogin();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    register.mutate(
      { email, username, password },
      {
        onSuccess: () => {
          // Auto-login after successful registration
          login.mutate({ email, password });
        },
      },
    );
  };

  const isPending = register.isPending || login.isPending;

  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-6">
      <h1 className="mb-1 text-xl font-bold text-white">Create account</h1>
      <p className="mb-6 text-sm text-white/40">
        Start tracking on-chain intelligence.
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
          label="Username"
          type="text"
          placeholder="satoshi"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoComplete="username"
        />
        <Input
          label="Password"
          type="password"
          placeholder="At least 8 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          autoComplete="new-password"
        />
        <Button type="submit" loading={isPending} size="lg" className="mt-1 w-full">
          Create account
        </Button>
      </form>

      <p className="mt-5 text-center text-xs text-white/40">
        Already have an account?{" "}
        <Link href="/login" className="text-brand hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
