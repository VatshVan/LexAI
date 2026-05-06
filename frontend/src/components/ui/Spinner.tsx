export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizeClass = { sm: "w-3 h-3", md: "w-5 h-5", lg: "w-8 h-8" }[size];
  return (
    <div className={`${sizeClass} border-2 border-accent border-t-transparent rounded-full animate-spin`} />
  );
}
