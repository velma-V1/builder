// Structure-only placeholder — not installed, not run in this repository state.
//
// Mirrors factory.ui_studio.design_tokens.default_token_set() exactly. When UI Studio renders a
// project, generated `ui/src/tokens/<template-id>.tokens.json` files (see fake_renderer.py) are the
// source of truth; this file is the shared default applied before any project-specific override.

export interface TokenSet {
  colors: Record<string, string>;
  spacing: Record<string, string>;
  typography: Record<string, string>;
  radii: Record<string, string>;
  motion: Record<string, string>;
}

export const defaultTokens: TokenSet = {
  colors: {
    background: "#ffffff",
    foreground: "#0a0a0a",
    primary: "#1d4ed8",
    "primary-foreground": "#ffffff",
    border: "#e5e7eb",
    muted: "#6b7280",
  },
  spacing: { xs: "0.25rem", sm: "0.5rem", md: "1rem", lg: "1.5rem", xl: "2rem" },
  typography: {
    "font-sans": "Inter, system-ui, sans-serif",
    "font-mono": "JetBrains Mono, monospace",
    "text-base": "1rem",
    "text-lg": "1.125rem",
  },
  radii: { sm: "0.25rem", md: "0.5rem", lg: "0.75rem" },
  motion: {
    "duration-fast": "120ms",
    "duration-normal": "200ms",
    "easing-standard": "cubic-bezier(0.4,0,0.2,1)",
  },
};

function applyTokensToRoot(tokens: TokenSet): void {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(tokens.colors)) {
    root.style.setProperty(`--color-${key}`, value);
  }
  for (const [key, value] of Object.entries(tokens.spacing)) {
    root.style.setProperty(`--spacing-${key}`, value);
  }
  for (const [key, value] of Object.entries(tokens.radii)) {
    root.style.setProperty(`--radius-${key}`, value);
  }
  for (const [key, value] of Object.entries(tokens.motion)) {
    root.style.setProperty(`--motion-${key}`, value);
  }
}

applyTokensToRoot(defaultTokens);
