'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('App Error:', error);
  }, [error]);

  return (
    <div className="flex h-screen w-full items-center justify-center bg-black text-white p-6">
      <div className="max-w-md w-full bg-[var(--surface-1)] border border-rose-500/20 rounded-3xl p-8 text-center space-y-6 shadow-2xl shadow-rose-900/20">
        <div className="w-16 h-16 bg-rose-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-8 h-8 text-rose-500" />
        </div>
        <h2 className="text-2xl font-black text-white tracking-tight">Something went wrong!</h2>
        <p className="text-sm text-gray-400">
          We encountered an unexpected error. This might be due to network issues or an invalid state.
        </p>
        <button
          onClick={() => reset()}
          className="w-full py-3.5 rounded-xl bg-[var(--surface-2)] hover:bg-[var(--surface-3)] border border-[var(--border-default)] text-sm font-semibold text-white flex items-center justify-center gap-2 transition-all"
        >
          <RefreshCw className="w-4 h-4 text-indigo-400" /> Try Again
        </button>
      </div>
    </div>
  );
}
