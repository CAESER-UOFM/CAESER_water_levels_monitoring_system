'use client';

import { ReactNode, useEffect, useState } from 'react';
import { MinimalLoadingScreen } from './MinimalLoadingScreen';

interface AppShellProps {
  children: ReactNode;
  loadingMessage?: string;
  minimumLoadingTime?: number; // Minimum time to show loading (prevents flash)
}

export function AppShell({
  children,
  loadingMessage = "Loading page...",
  minimumLoadingTime = 300
}: AppShellProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [startTime] = useState(Date.now());

  useEffect(() => {
    const finishLoading = () => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, minimumLoadingTime - elapsed);

      setTimeout(() => {
        setIsLoading(false);
      }, remaining);
    };

    // Start loading process
    const timer = setTimeout(finishLoading, 100);

    return () => clearTimeout(timer);
  }, [startTime, minimumLoadingTime]);

  if (isLoading) {
    return <MinimalLoadingScreen message={loadingMessage} progress={85} />;
  }

  return <>{children}</>;
}