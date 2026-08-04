"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bell,
  Coins,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Settings,
  Trophy,
  Wallet,
} from "lucide-react";
import { clsx } from "clsx";
import { useLogout } from "@/hooks/useAuth";
import { useAuthStore } from "@/store/auth";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/wallets", label: "Wallets", icon: Wallet },
  { href: "/dashboard/rankings", label: "Rankings", icon: Trophy },
  { href: "/dashboard/alerts", label: "Alerts", icon: Bell },
  { href: "/dashboard/tokens", label: "Tokens", icon: Coins },
  { href: "/dashboard/paper-trading", label: "Paper Trade", icon: FlaskConical },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const logout = useLogout();
  const user = useAuthStore((s) => s.user);

  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-surface-border bg-surface-card">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-surface-border px-4">
        <Activity className="h-5 w-5 text-brand" />
        <span className="text-sm font-bold tracking-wide text-white">
          PUMP<span className="text-brand">WATCH</span>
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-0.5 p-2 pt-3">
        {NAV.map(({ href, label, icon: Icon, exact }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand/10 text-brand"
                  : "text-white/50 hover:bg-surface-elevated hover:text-white",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User + logout */}
      <div className="border-t border-surface-border p-3">
        {user && (
          <div className="mb-2 px-2">
            <p className="truncate text-xs font-medium text-white/80">
              {user.username}
            </p>
            <p className="truncate text-xs text-white/40">{user.email}</p>
          </div>
        )}
        <button
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-white/40 transition-colors hover:bg-surface-elevated hover:text-danger"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
