import { useCallback, useEffect, useState } from "react";

// The single source of truth for theme. The persisted preference (if any) wins;
// otherwise the OS `prefers-color-scheme` is the default; otherwise (no
// matchMedia at all — older/headless env) light. The chosen value is persisted
// to localStorage so it survives reloads, and the document root carries BOTH the
// `.dark` class (what Tailwind's darkMode:"class" keys off) and a
// `data-theme` attribute (what the token CSS aliases), kept in sync here.
export type Theme = "light" | "dark";

const THEME_KEY = "dwcoa.theme";

function readStored(): Theme | null {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null;
  }
}

function prefersDark(): boolean {
  try {
    if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
  } catch {
    /* fall through to light */
  }
  return false;
}

function getInitialTheme(): Theme {
  const stored = readStored();
  if (stored) return stored;
  return prefersDark() ? "dark" : "light";
}

function applyTheme(theme: Theme) {
  const el = document.documentElement;
  if (theme === "dark") {
    el.classList.add("dark");
    el.setAttribute("data-theme", "dark");
  } else {
    el.classList.remove("dark");
    el.setAttribute("data-theme", "light");
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch {
        /* persistence is best-effort */
      }
      return next;
    });
  }, []);

  return { theme, isDark: theme === "dark", toggle };
}
