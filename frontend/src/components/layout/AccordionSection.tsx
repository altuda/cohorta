import type { ReactNode } from "react";

interface Props {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}

/** Collapsible sidebar section. Only its header shows when collapsed. */
export default function AccordionSection({
  title,
  isOpen,
  onToggle,
  children,
}: Props) {
  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        aria-expanded={isOpen}
        className="w-full px-3 py-2.5 flex items-center justify-between bg-white hover:bg-slate-50 text-left"
      >
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
          {title}
        </span>
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`w-4 h-4 text-slate-400 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      {isOpen && (
        <div className="px-3 pb-3 pt-2 border-t border-slate-100">{children}</div>
      )}
    </div>
  );
}
