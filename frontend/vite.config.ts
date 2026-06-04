/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

const fromHere = (p: string) => fileURLToPath(new URL(p, import.meta.url));

// The Foundation frontend tests live outside this package (under features/),
// so Node can't walk up to frontend/node_modules. Alias the bare specifiers
// those test files pull directly to this package's installed copies.
const externalTestDeps = [
  "react",
  "react-dom",
  "@testing-library/react",
  "@testing-library/jest-dom",
  "vitest",
];

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: "@", replacement: fromHere("./src") },
      ...externalTestDeps.map((name) => ({
        find: new RegExp(`^${name}(/.*)?$`),
        replacement: fromHere(`./node_modules/${name}`) + "$1",
      })),
    ],
  },
  server: {
    fs: { allow: [fromHere("..")] },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["../features/foundation-001/tests/frontend/**/*.test.{ts,tsx}"],
  },
});
