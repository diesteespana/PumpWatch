"use client";

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  return (
    <div className="flex h-14 items-center justify-between border-b border-surface-border px-6">
      <div>
        <h1 className="text-sm font-semibold text-white">{title}</h1>
        {subtitle && (
          <p className="text-xs text-white/40">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
