'use client';

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';

export function usePerformanceMetrics() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // 1. Initial Load Metrics
    if (typeof window !== 'undefined' && window.performance) {
      const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      if (navEntry) {
        const loadTime = navEntry.loadEventEnd - navEntry.startTime;
        const domReady = navEntry.domContentLoadedEventEnd - navEntry.startTime;
        console.debug(`[Perf] Initial Load: ${Math.round(loadTime)}ms | DOM Ready: ${Math.round(domReady)}ms`);
      }
    }
  }, []);

  useEffect(() => {
    // 2. Route Transition Metrics
    const startTime = performance.now();
    
    return () => {
      const timeSpent = performance.now() - startTime;
      console.debug(`[Perf] Route Transition / Unmount (${pathname}): ${Math.round(timeSpent)}ms`);
    };
  }, [pathname, searchParams]);
}
