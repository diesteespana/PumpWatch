"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { apiGet, apiPost } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { queryClient } from "@/lib/queryClient";
import type { TokenPair, User } from "@/types/api";

export function useMe() {
  const accessToken = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<User>("/users/me"),
    enabled: !!accessToken,
  });
}

export function useLogin() {
  const { setTokens, setUser } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      apiPost<TokenPair>("/auth/login", { email, password }),
    onSuccess: async (data) => {
      setTokens(data.access_token, data.refresh_token);
      const user = await apiGet<User>("/users/me");
      setUser(user);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      router.push("/dashboard");
    },
    onError: () => {
      toast.error("Invalid email or password");
    },
  });
}

export function useRegister() {
  const { setTokens, setUser } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: ({
      email,
      username,
      password,
    }: {
      email: string;
      username: string;
      password: string;
    }) => apiPost<User>("/auth/register", { email, username, password }),
    onSuccess: async () => {
      // Auto-login after register
      toast.success("Account created!");
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Registration failed";
      toast.error(msg);
    },
  });
}

export function useLogout() {
  const { refreshToken, clearAuth } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: async () => {
      if (refreshToken) {
        await apiPost("/auth/logout", { refresh_token: refreshToken }).catch(
          () => {},
        );
      }
    },
    onSettled: () => {
      clearAuth();
      queryClient.clear();
      router.push("/login");
    },
  });
}
