// Phase 1 activation: dependencies pinned in package.json and installed.
// @storybook/addon-essentials was removed upstream in Storybook v9 — its viewport/controls/
// interactions/actions addons moved into storybook core, so it is intentionally not listed here.
import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../stories/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-a11y"],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
};

export default config;
