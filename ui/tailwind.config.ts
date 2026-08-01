// Loaded via the @config directive in src/index.css (Tailwind v4's CSS-first config still
// supports a JS/TS config file this way). Token values here must stay in sync with the backend
// design-token contract emitted by factory.ui_studio.design_tokens (see src/tokens/index.ts,
// which re-exports the same values).
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}", "./stories/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        primary: {
          DEFAULT: "var(--color-primary)",
          foreground: "var(--color-primary-foreground)",
        },
        border: "var(--color-border)",
        muted: "var(--color-muted)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
      spacing: {
        xs: "var(--spacing-xs)",
        sm: "var(--spacing-sm)",
        md: "var(--spacing-md)",
        lg: "var(--spacing-lg)",
        xl: "var(--spacing-xl)",
      },
      transitionDuration: {
        fast: "var(--motion-duration-fast)",
        normal: "var(--motion-duration-normal)",
      },
    },
  },
  plugins: [],
} satisfies Config;
