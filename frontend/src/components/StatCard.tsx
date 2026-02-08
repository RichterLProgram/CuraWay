import { ReactNode, forwardRef } from "react";
import { motion } from "framer-motion";

interface StatCardProps {
  title: string;
  value: string | number;
  variant: "demand" | "supply" | "warning" | "neutral";
  icon?: ReactNode;
  subtitle?: string;
  delay?: number;
}

const StatCard = forwardRef<HTMLDivElement, StatCardProps>(({ title, value, variant, icon, subtitle, delay = 0 }, ref) => {
  const borderClass = {
    demand: "stat-card-demand",
    supply: "stat-card-supply",
    warning: "stat-card-warning",
    neutral: "stat-card-neutral",
  }[variant];

  const gradientClass = {
    demand: "gradient-demand",
    supply: "gradient-supply",
    warning: "gradient-warning",
    neutral: "",
  }[variant];

  const textClass = {
    demand: "text-gradient-red",
    supply: "text-gradient-green",
    warning: "text-gradient-amber",
    neutral: "text-foreground",
  }[variant];

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className={`glass rounded-2xl p-5 ${borderClass} ${gradientClass} transition-all duration-300 hover:scale-[1.02]`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.15em]">{title}</p>
          <p className={`text-3xl font-bold mt-1.5 tracking-tight ${textClass}`}>{value}</p>
          {subtitle && <p className="text-[11px] text-muted-foreground mt-1">{subtitle}</p>}
        </div>
        {icon && <div className="text-muted-foreground/30">{icon}</div>}
      </div>
    </motion.div>
  );
});

StatCard.displayName = "StatCard";

export default StatCard;
