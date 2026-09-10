/** Favicon mark: lens, bug body, two spots. No legs, antennae, or git trunk. */
export function SimplifiedMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <circle cx="16" cy="14" r="9" />
      <path d="M22.5 20.5L27 25" strokeWidth={2.6} />
      <ellipse cx="16" cy="15.5" rx="3.2" ry="3.8" fill="currentColor" stroke="none" />
      <circle cx="14.8" cy="14.5" r="0.75" fill="currentColor" stroke="none" />
      <circle cx="17.2" cy="16.5" r="0.75" fill="currentColor" stroke="none" />
    </svg>
  );
}

export default function Icon() {
  return (
    <span className="bg-primary text-primary-foreground inline-flex size-full items-center justify-center rounded-md">
      <SimplifiedMark className="size-[62%]" />
    </span>
  );
}
