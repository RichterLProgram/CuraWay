import { Users, Building2, AlertTriangle, BarChart3 } from "lucide-react";
import { motion } from "framer-motion";
import StatCard from "./StatCard";
import type { DemandData, SupplyData, GapAnalysis } from "@/types/healthgrid";

interface DemandTabProps {
  data?: DemandData;
  supply?: SupplyData;
  gap?: GapAnalysis;
}

const DemandTab = ({ data, supply, gap }: DemandTabProps) => {
  if (!data || !supply || !gap) {
    return (
      <div className="glass rounded-2xl p-4 text-xs text-muted-foreground">
        Loading demand insights...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <StatCard title="Demand" value={data.total_count.toLocaleString()} variant="demand" icon={<Users size={16} />} subtitle="Active cases" delay={0.05} />
        <StatCard title="Facilities" value={supply.total_count} variant="supply" icon={<Building2 size={16} />} subtitle="Registered" delay={0.1} />
        <StatCard title="Deserts" value={gap.deserts.length} variant="warning" icon={<AlertTriangle size={16} />} subtitle="Detected" delay={0.15} />
        <StatCard title="Coverage" value={`${supply.avg_coverage}%`} variant="neutral" icon={<BarChart3 size={16} />} subtitle="Average" delay={0.2} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.25 }}
        className="glass rounded-2xl p-4 space-y-3"
      >
        <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.15em]">Top Diagnoses</h3>
        {data.top_diagnoses.map((d, i) => {
          const pct = (d.count / data.total_count) * 100;
          return (
            <motion.div
              key={d.name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.3 + i * 0.05 }}
            >
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium">{d.name}</span>
                <span className="text-muted-foreground font-mono">{d.count}</span>
              </div>
              <div className="h-1 rounded-full bg-muted overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: "linear-gradient(90deg, hsl(var(--demand)), hsl(0 90% 70%))" }}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.7, delay: 0.35 + i * 0.05 }}
                />
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.5 }}
        className="glass rounded-2xl p-4"
      >
        <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.15em] mb-3">Recent Cases</h3>
        {data.points.slice(0, 5).map((p, i) => (
          <motion.div
            key={p.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.55 + i * 0.04 }}
            className="flex items-center justify-between py-2.5 border-b border-border/30 last:border-0 text-xs"
          >
            <div className="flex items-center gap-2.5">
              <span className={`w-1.5 h-1.5 rounded-full ${p.urgency >= 8 ? "bg-demand" : p.urgency >= 5 ? "bg-warning" : "bg-supply"}`} />
              <span className="font-medium">{p.diagnosis}</span>
              <span className="text-muted-foreground">{p.region}</span>
            </div>
            <span className={`font-mono font-semibold text-[10px] px-1.5 py-0.5 rounded ${p.urgency >= 8 ? "bg-demand/10 text-demand" : p.urgency >= 5 ? "bg-warning/10 text-warning" : "bg-supply/10 text-supply"}`}>
              U{p.urgency}
            </span>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
};

export default DemandTab;
