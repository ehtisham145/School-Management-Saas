import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function base(props: IconProps) {
  return {
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    ...props,
  };
}

export function AttendanceIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="5" y="3.5" width="14" height="17" rx="1" />
      <path d="M9 3.5V6h6V3.5" />
      <path d="M8.5 12l2 2 4.5-4.5" />
    </svg>
  );
}

export function ExamsIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M5 19V9M11 19V5M17 19v-6" />
      <path d="M4 19h16" />
    </svg>
  );
}

export function FeesIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M5 5h11l3 3.2V19H5z" />
      <path d="M8 10h7M8 13.3h7" />
      <path d="M5 19.3l1.6-1 1.6 1 1.6-1 1.6 1 1.6-1 1.6 1 1.6-1 1.6 1" />
    </svg>
  );
}

export function TimetableIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="4" y="4.5" width="16" height="15" rx="1" />
      <path d="M4 9.5h16M9.3 4.5v15M14.7 4.5v15" />
    </svg>
  );
}

export function MessagesIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 5.5h16v10H9l-3.5 3.2V15.5H4z" />
    </svg>
  );
}

export function BilingualIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M8.5 4v16M4 7h4.5M4 17h4.5" />
      <path d="M15.5 4v16M15.5 7H20M15.5 17H20" />
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M5 12.5l4.5 4.5L19 7" />
    </svg>
  );
}

export function ArrowIcon(props: IconProps) {
  return (
    <svg {...base({ strokeWidth: 1.8, ...props })}>
      <path d="M7 17L17 7M9 7h8v8" />
    </svg>
  );
}

export function ChatIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="4" y="5" width="16" height="12" rx="6" />
      <polygon points="8.5,17 8.5,20.5 12,17" fill="currentColor" stroke="none" />
      <circle cx="9" cy="11" r="1" fill="currentColor" stroke="none" />
      <circle cx="12" cy="11" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="11" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function MailIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="3.5" y="5.5" width="17" height="13" rx="1" />
      <path d="M4 6.5l8 6.3 8-6.3" />
    </svg>
  );
}

export function CalendarIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="4" y="5" width="16" height="15" rx="1.5" />
      <path d="M4 9.5h16M8 3.5v3M16 3.5v3" />
    </svg>
  );
}

export function RolesIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="9" cy="8" r="2.6" />
      <path d="M4 19c0-2.8 2.2-5 5-5s5 2.2 5 5" />
      <circle cx="17.5" cy="7.5" r="2" />
      <path d="M15.8 13c2.2.3 3.9 2.2 3.9 4.5" />
    </svg>
  );
}

export function LocationIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 21s-7-6.3-7-11.5A7 7 0 0112 2.5a7 7 0 017 7C19 14.7 12 21 12 21z" />
      <circle cx="12" cy="9.5" r="2.3" />
    </svg>
  );
}

export function BrandMark(props: IconProps) {
  return (
    <svg viewBox="0 0 30 30" fill="none" aria-hidden {...props}>
      <path d="M4 3h18v24H4" stroke="currentColor" strokeWidth="1.6" />
      <line x1="9" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="1.4" />
      <line x1="9" y1="14.5" x2="17" y2="14.5" stroke="currentColor" strokeWidth="1.4" />
      <line x1="9" y1="19" x2="14" y2="19" stroke="currentColor" strokeWidth="1.4" />
      <rect x="22" y="9" width="5" height="5" fill="var(--primary)" stroke="none" />
    </svg>
  );
}
