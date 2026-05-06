import { ButtonHTMLAttributes, ReactNode } from "react";

import { Spinner } from "./Spinner";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  loading,
  children,
  disabled,
  className = "",
  ...rest
}: Props) {
  const base =
    "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none disabled:opacity-40 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-accent text-white hover:bg-blue-600",
    ghost: "border border-surface-600 text-gray-300 hover:bg-surface-700",
    danger: "bg-red-600 text-white hover:bg-red-700"
  };
  return (
    <button
      className={`${base} ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
