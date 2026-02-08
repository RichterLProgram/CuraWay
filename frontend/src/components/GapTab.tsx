import { motion } from "framer-motion";
import { AlertTriangle, TrendingUp, MapPin, Zap } from "lucide-react";
import StatCard from "./StatCard";
import type { GapAnalysis, PlannerRecommendations } from "@/types/healthgrid";

interface GapTabProps {
  data?: GapAnalysis;
  recommendations?: PlannerRecommendations;
}

const priorityStyles: Record<string, string> = {
  critical: "bg-demand/15 text-demand border-demand/30",
  high: "bg-warning/15 text-warning border-warning/30",
  medium: "bg-supply/15 text-supply border-supply/30",
  low: "bg-muted text-muted-foreground border-border",
};

const GapTab = ({ data, recommendations }: GapTabProps) => {
  if (!data || !recommendations) {
    return (
      <div className="glass rounded-2xl p-4 text-xs text-muted-foreground">
        Loading gap analysis...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <StatCard title="Deserts" value={data.deserts.length} variant="warning" icon={<AlertTriangle size={14} />} delay={0.05} />
        <StatCard title="Underserved" value={`${(data.total_population_underserved / 1000).toFixed(0)}K`} variant="demand" delay={0.1} />
        <StatCard title="Gap Score" value={`${(data.avg_gap_score * 100).toFixed(0)}%`} variant="warning" delay={0.15} />
      </div>

      {/* Deserts */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="space-y-2"
      >
        <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.15em] px-1">Medical Deserts</h3>
        {data.deserts.map((d, i) => (
          <motion.div
            key={d.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.25 + i * 0.04 }}
            className="glass rounded-xl p-3.5 gradient-warning"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">!</span>
                <div>
                  <h4 className="font-semibold text-xs">{d.region_name}</h4>
                  <p className="text-[10px] text-muted-foreground">{d.nearest_facility_km}km · {d.population_affected.toLocaleString()} people</p>
                </div>
              </div>
              <span className="text-sm font-bold text-gradient-amber">{(d.gap_score * 100).toFixed(0)}%</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {d.missing_capabilities.map((cap) => (
                <span key={cap} className="px-1.5 py-0.5 text-[9px] font-medium rounded bg-warning/10 text-warning/80 border border-warning/15">
                  {cap}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Recommendations */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
        className="space-y-2"
      >
        <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.15em] flex items-center gap-1.5 px-1">
          <Zap size={10} className="text-warning" /> AI Recommendations
        </h3>
        {recommendations.recommendations.map((r, i) => (
          <motion.div
            key={r.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 + i * 0.05 }}
            className="glass rounded-xl p-4 transition-all duration-200 hover:scale-[1.01]"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className={`px-1.5 py-0.5 text-[8px] font-bold uppercase rounded border ${priorityStyles[r.priority]}`}>
                    {r.priority}
                  </span>
                  <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                    <MapPin size={8} /> {r.region}
                  </span>
                </div>
                <h4 className="font-semibold text-xs">{r.action}</h4>
                <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{r.capability_needed}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-xl font-bold text-gradient-green leading-none">{r.lives_saved_per_year}</div>
                <div className="text-[9px] text-muted-foreground mt-0.5">lives/yr</div>
              </div>
            </div>
            <div className="mt-3 pt-2.5 border-t border-border/20 flex items-center justify-between text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1 truncate"><TrendingUp size={10} className="text-supply flex-shrink-0" /> {r.estimated_impact}</span>
              <span className="font-mono font-semibold text-foreground/60 flex-shrink-0 ml-2">ROI: {r.roi}</span>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
};

export default GapTab;
