import { motion } from "framer-motion";
import { Building2, MapPin, Stethoscope, BedDouble } from "lucide-react";
import type { SupplyData } from "@/types/healthgrid";

interface SupplyTabProps {
  data?: SupplyData;
}

const SupplyTab = ({ data }: SupplyTabProps) => {
  if (!data) {
    return (
      <div className="glass rounded-2xl p-4 text-xs text-muted-foreground">
        Loading supply insights...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="glass rounded-2xl p-4"
      >
        <div className="flex items-baseline justify-between mb-3">
          <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.15em]">Overview</h3>
          <div className="flex items-baseline gap-4 text-xs text-muted-foreground">
            <span><span className="text-gradient-green font-bold text-base">{data.total_count}</span> facilities</span>
            <span><span className="text-gradient-green font-bold text-base">{data.avg_coverage}%</span> avg coverage</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {data.top_capabilities.map((c, i) => (
            <motion.span
              key={c.name}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 + i * 0.04 }}
              className="px-2.5 py-1 text-[10px] font-medium rounded-md bg-supply/10 text-supply border border-supply/15"
            >
              {c.name} ({c.count})
            </motion.span>
          ))}
        </div>
      </motion.div>

      <div className="space-y-2">
        {data.facilities.map((f, i) => (
          <motion.div
            key={f.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 + i * 0.04 }}
            className="glass rounded-xl p-4 transition-all duration-200 hover:scale-[1.01] hover:border-supply/20"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-supply/10 flex items-center justify-center flex-shrink-0">
                  <Building2 size={14} className="text-supply" />
                </div>
                <div>
                  <h4 className="font-semibold text-xs leading-tight">{f.name}</h4>
                  <p className="text-[10px] text-muted-foreground flex items-center gap-1 mt-0.5">
                    <MapPin size={8} /> {f.region}
                  </p>
                </div>
              </div>
              <span className="text-sm font-bold text-gradient-green">{f.coverage}%</span>
            </div>

            <div className="mt-2.5 flex items-center gap-3 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1"><BedDouble size={10} /> {f.beds}</span>
              <span className="flex items-center gap-1"><Stethoscope size={10} /> {f.staff}</span>
              <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden ml-2">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: "linear-gradient(90deg, hsl(var(--supply)), hsl(160 80% 65%))" }}
                  initial={{ width: 0 }}
                  animate={{ width: `${f.coverage}%` }}
                  transition={{ duration: 0.6, delay: 0.2 + i * 0.04 }}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default SupplyTab;
