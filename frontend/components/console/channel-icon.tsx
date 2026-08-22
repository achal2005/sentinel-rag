import type { Channel } from "@/lib/types";

const LABEL: Record<Channel, string> = {
  email: "Email",
  whatsapp: "WhatsApp",
  web_form: "Web form",
};

/** The channel a request arrived on. Icon is neutral — status carries color. */
export function ChannelIcon({ channel, className }: { channel: Channel; className?: string }) {
  const cls = className ?? "size-4";
  const title = LABEL[channel];
  if (channel === "email") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" role="img" aria-label={title}>
        <rect x="3" y="5" width="18" height="14" rx="2.5" />
        <path d="m3.5 7 8.5 6 8.5-6" />
      </svg>
    );
  }
  if (channel === "whatsapp") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" role="img" aria-label={title}>
        <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-4-1L3 21l2-5.5a8.38 8.38 0 0 1-1-4A8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5Z" />
        <path d="M8.7 8.9c-.2 0-.5.1-.6.3-.3.3-.7.8-.7 1.7 0 1 .7 2 .8 2.1.1.2 1.5 2.4 3.7 3.2 1.8.7 2.2.6 2.6.5.5-.1 1.2-.5 1.3-1 .2-.5.2-.9.1-1-.1-.1-.2-.2-.5-.3l-1.4-.6c-.2-.1-.4-.1-.5.1l-.6.7c-.1.2-.3.2-.5.1a4.9 4.9 0 0 1-2.4-2.1c-.1-.2 0-.4.1-.5l.4-.5c.1-.2.1-.3 0-.5l-.6-1.3c-.1-.3-.3-.3-.5-.3Z" fill="currentColor" stroke="none" />
      </svg>
    );
  }
  return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" role="img" aria-label={title}>
      <rect x="3" y="4" width="18" height="16" rx="2.5" />
      <path d="M3 8h18" />
      <path d="M7 12h7M7 15.5h10" />
    </svg>
  );
}

export function channelLabel(channel: Channel): string {
  return LABEL[channel];
}
