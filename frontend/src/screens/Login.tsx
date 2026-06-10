import { useState, type FormEvent } from "react";
import { Building2 } from "@/icons";
import { Button } from "@/primitives";

// Re-skinned two-panel branded login. Behavior is preserved exactly: submitting
// POSTs /api/auth/login {password}; 200 → refresh auth; 429 → rate-limit
// message; other non-2xx → "Incorrect password." No role selector — the
// password determines the role server-side (visual-redesign-009 US-4).
export default function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      onAuthenticated();
    } else if (res.status === 429) {
      setError("Too many attempts. Please wait and try again.");
    } else {
      setError("Incorrect password.");
    }
  }

  return (
    <main className="flex min-h-screen w-full flex-col md:flex-row">
      {/* Brand panel */}
      <section
        aria-hidden="true"
        className="relative hidden flex-col justify-between p-12 text-white md:flex md:w-[52%]"
        style={{
          background:
            "linear-gradient(135deg, #0D5638 0%, #0A2B1E 100%)",
        }}
      >
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-[9px] bg-white/15">
            <Building2 size={20} />
          </span>
          <div className="leading-tight">
            <div className="text-[15px] font-bold">DWCOA Financials</div>
            <div className="text-[11px] text-white/70">
              Denny Way Condo Owners Association
            </div>
          </div>
        </div>
        <div className="max-w-md">
          <h2 className="text-[32px] font-bold leading-tight tracking-[-0.03em]">
            Every dollar across nine homes, in one clear ledger.
          </h2>
          <div className="mt-6 flex gap-8 text-[13px] text-white/80">
            <div>
              <div className="tnum text-[20px] font-bold text-white">9</div>
              Units
            </div>
            <div>
              <div className="tnum text-[20px] font-bold text-white">1</div>
              Association
            </div>
          </div>
        </div>
        <p className="text-[12px] text-white/50">Board-only access · Seattle, WA</p>
      </section>

      {/* Form panel */}
      <section className="flex flex-1 items-center justify-center bg-bg px-6 py-16">
        <div className="w-full max-w-[340px]">
          <h1 className="text-[23px] font-bold tracking-[-0.02em] text-ink">
            Welcome back
          </h1>
          <p className="mt-1 text-[13px] text-ink-2">
            Sign in to view the association's finances.
          </p>
          <form onSubmit={handleSubmit} aria-label="Log in" className="mt-8 space-y-4">
            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-[12.5px] font-semibold text-ink-2"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-11 w-full rounded-ctrl border border-border-2 bg-surface px-3 text-[14px] text-ink outline-none"
              />
            </div>
            <Button type="submit" variant="primary" className="h-11 w-full">
              Log in
            </Button>
            {error && (
              <p role="alert" className="text-[13px] font-medium text-neg">
                {error}
              </p>
            )}
          </form>
        </div>
      </section>
    </main>
  );
}
