'use client';

import { useState, useEffect, useCallback } from 'react';

interface LoadingStage {
  name: string;
  message: string;
  weight: number; // Relative weight for progress calculation
}

const LOADING_STAGES: LoadingStage[] = [
  { name: 'core', message: 'Loading core components...', weight: 20 },
  { name: 'database', message: 'Connecting to database...', weight: 25 },
  { name: 'charts', message: 'Loading visualization tools...', weight: 30 },
  { name: 'maps', message: 'Loading mapping components...', weight: 15 },
  { name: 'complete', message: 'Finalizing setup...', weight: 10 }
];

export interface UseProgressiveAppLoadingReturn {
  isLoading: boolean;
  progress: number;
  currentMessage: string;
  currentStage: string;
  completeStage: (stageName: string) => void;
  setCustomMessage: (message: string) => void;
}

export function useProgressiveAppLoading(): UseProgressiveAppLoadingReturn {
  const [completedStages, setCompletedStages] = useState<Set<string>>(new Set());
  const [currentStage, setCurrentStage] = useState<string>('core');
  const [customMessage, setCustomMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  // Calculate progress based on completed stages
  const progress = LOADING_STAGES.reduce((acc, stage) => {
    if (completedStages.has(stage.name)) {
      return acc + stage.weight;
    }
    return acc;
  }, 0);

  // Get current message
  const getCurrentMessage = useCallback(() => {
    if (customMessage) return customMessage;

    const activeStage = LOADING_STAGES.find(stage =>
      !completedStages.has(stage.name)
    );

    return activeStage?.message || 'Loading complete!';
  }, [completedStages, customMessage]);

  const currentMessage = getCurrentMessage();

  const completeStage = useCallback((stageName: string) => {
    setCompletedStages(prev => new Set([...prev, stageName]));

    // Find next stage
    const nextStageIndex = LOADING_STAGES.findIndex(stage => stage.name === stageName) + 1;
    if (nextStageIndex < LOADING_STAGES.length) {
      setCurrentStage(LOADING_STAGES[nextStageIndex].name);
    } else {
      // All stages complete
      setTimeout(() => {
        setIsLoading(false);
      }, 500); // Small delay to show completion
    }
  }, []);

  const setCustomMessageHandler = useCallback((message: string) => {
    setCustomMessage(message);
  }, []);

  // Auto-complete core stage after minimal delay
  useEffect(() => {
    const timer = setTimeout(() => {
      completeStage('core');
    }, 300);

    return () => clearTimeout(timer);
  }, [completeStage]);

  return {
    isLoading,
    progress,
    currentMessage,
    currentStage,
    completeStage,
    setCustomMessage: setCustomMessageHandler
  };
}