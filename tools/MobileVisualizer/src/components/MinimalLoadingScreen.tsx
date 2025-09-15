'use client';

interface MinimalLoadingScreenProps {
  progress?: number;
  message?: string;
}

export function MinimalLoadingScreen({
  progress = 0,
  message = "Loading CAESER Water Level Visualizer..."
}: MinimalLoadingScreenProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-blue-900 flex items-center justify-center">
      <div className="text-center px-4 max-w-md mx-auto">
        {/* CAESER Mascot with breathing animation */}
        <div className="w-32 h-32 rounded-full flex items-center justify-center shadow-2xl mb-8 mx-auto overflow-hidden animate-pulse-gentle">
          <img
            src="/caeser-mascot.png"
            alt="CAESER Loading"
            className="w-full h-full object-contain"
          />
        </div>

        <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent mb-4">
          CAESER
        </h1>

        <h2 className="text-xl font-bold text-white mb-6">
          Water Levels Visualizer
        </h2>

        {/* Loading Progress */}
        <div className="w-full bg-gray-700 rounded-full h-2 mb-4">
          <div
            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>

        {/* Loading Message */}
        <p className="text-gray-300 text-sm animate-pulse">
          {message}
        </p>

        {/* Loading Spinner */}
        <div className="flex items-center justify-center mt-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
        </div>

        {/* Progress Percentage */}
        {progress > 0 && (
          <p className="text-cyan-400 text-xs mt-4 font-medium">
            {Math.round(progress)}%
          </p>
        )}
      </div>
    </div>
  );
}