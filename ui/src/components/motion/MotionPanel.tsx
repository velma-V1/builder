// Motion (formerly Framer Motion) wrapper honoring the shared duration/easing tokens.
import { motion } from "motion/react";
import type { JSX, ReactNode } from "react";

export interface MotionPanelProps {
  children: ReactNode;
}

export function MotionPanel({ children }: MotionPanelProps): JSX.Element {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
    >
      {children}
    </motion.div>
  );
}
