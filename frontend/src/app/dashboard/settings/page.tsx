"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Send, MessageSquare, Mail } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { apiGet, apiPut } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import type { NotificationSetting, NotificationChannel } from "@/types/api";

function useNotificationSettings() {
  return useQuery({
    queryKey: ["notification-settings"],
    queryFn: () => apiGet<NotificationSetting[]>("/notifications/settings"),
  });
}

function useUpdateSetting() {
  return useMutation({
    mutationFn: ({
      channel,
      is_active,
      config,
    }: {
      channel: NotificationChannel;
      is_active: boolean;
      config: Record<string, string>;
    }) => apiPut<NotificationSetting>("/notifications/settings", { channel, is_active, config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-settings"] });
      toast.success("Settings saved");
    },
    onError: () => toast.error("Failed to save settings"),
  });
}

interface ChannelCardProps {
  title: string;
  icon: React.ElementType;
  channel: NotificationChannel;
  fields: { key: string; label: string; placeholder: string; type?: string }[];
  existing?: NotificationSetting;
}

function ChannelCard({ title, icon: Icon, channel, fields, existing }: ChannelCardProps) {
  const [active, setActive] = useState(existing?.is_active ?? false);
  const [values, setValues] = useState<Record<string, string>>(
    existing?.config ?? {},
  );
  const update = useUpdateSetting();

  useEffect(() => {
    if (existing) {
      setActive(existing.is_active);
      setValues(existing.config);
    }
  }, [existing]);

  const onSave = (e: React.FormEvent) => {
    e.preventDefault();
    update.mutate({ channel, is_active: active, config: values });
  };

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="rounded-lg bg-brand/10 p-2">
            <Icon className="h-4 w-4 text-brand" />
          </div>
          <span className="font-semibold text-white">{title}</span>
        </div>
        <label className="flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
            className="h-4 w-4 accent-brand"
          />
          <span className="text-xs text-white/50">Enabled</span>
        </label>
      </div>

      <form onSubmit={onSave} className="flex flex-col gap-3">
        {fields.map((f) => (
          <Input
            key={f.key}
            label={f.label}
            placeholder={f.placeholder}
            type={f.type ?? "text"}
            value={values[f.key] ?? ""}
            onChange={(e) =>
              setValues((prev) => ({ ...prev, [f.key]: e.target.value }))
            }
          />
        ))}
        <Button type="submit" loading={update.isPending} size="sm" className="self-end">
          Save
        </Button>
      </form>
    </div>
  );
}

export default function SettingsPage() {
  const { data: settings, isLoading } = useNotificationSettings();

  const get = (ch: NotificationChannel) =>
    settings?.find((s) => s.channel === ch);

  return (
    <>
      <Header title="Settings" subtitle="Notification channel configuration" />

      <div className="p-6">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <ChannelCard
              title="Telegram"
              icon={Send}
              channel="telegram"
              existing={get("telegram")}
              fields={[
                {
                  key: "chat_id",
                  label: "Chat ID",
                  placeholder: "@yourchannel or numeric ID",
                },
                {
                  key: "bot_token",
                  label: "Bot token (optional override)",
                  placeholder: "123456:ABC-…",
                },
              ]}
            />
            <ChannelCard
              title="Discord"
              icon={MessageSquare}
              channel="discord"
              existing={get("discord")}
              fields={[
                {
                  key: "webhook_url",
                  label: "Webhook URL",
                  placeholder: "https://discord.com/api/webhooks/…",
                },
              ]}
            />
            <ChannelCard
              title="Email"
              icon={Mail}
              channel="email"
              existing={get("email")}
              fields={[
                {
                  key: "to_address",
                  label: "Recipient email",
                  placeholder: "alerts@yourmail.com",
                  type: "email",
                },
              ]}
            />
          </div>
        )}
      </div>
    </>
  );
}
