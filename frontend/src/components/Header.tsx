import { motion } from "framer-motion";
import { ParticleButton } from "@/components/ui/particle-button";

interface HeaderProps {
  showIndicators?: boolean;
  indicators?: {
    demand: string;
    underserved: string;
    gapScore: string;
  };
  onTakeAction?: () => void;
}

const Header = ({ showIndicators = false, indicators, onTakeAction }: HeaderProps) => {
  return (
    <header className="healthgrid-header">
      <div className="max-w-[1400px] mx-auto px-10 pt-8 pb-4 flex items-center justify-between gap-6">
        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <button
            type="button"
            onClick={() => window.location.assign("/")}
            className="text-left"
          >
            <h1 className="text-xl font-semibold tracking-[0.2em] leading-none uppercase">CuraWay</h1>
            <p className="text-[9px] uppercase tracking-[0.2em] text-muted-foreground font-medium mt-0.5">
              Healthcare Intelligence
            </p>
          </button>
        </motion.div>
        <div className="flex items-center">
          {showIndicators && indicators && (
            <div className="glass rounded-xl px-4 py-2 flex flex-wrap items-center gap-6">
              <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                Key Indicators
              </div>
              <div className="flex items-center gap-6 text-sm">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                    Demand
                  </div>
                  <div className="text-lg font-semibold">{indicators.demand}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                    Underserved
                  </div>
                  <div className="text-lg font-semibold">{indicators.underserved}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                    Avg Gap Score
                  </div>
                  <div className="text-lg font-semibold">{indicators.gapScore}</div>
                </div>
              </div>
              {onTakeAction && (
                <button
                  onClick={onTakeAction}
                  className="text-[10px] uppercase tracking-[0.3em] text-white bg-demand/90 hover:bg-demand transition-colors rounded-full px-4 py-2 shadow-[0_0_20px_hsl(var(--demand)/0.35)]"
                >
                  Take Action
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
