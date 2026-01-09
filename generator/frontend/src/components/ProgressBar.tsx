interface ProgressBarProps {
  currentStep: number
  totalSteps: number
  stepLabels: string[]
}

export default function ProgressBar({ currentStep, totalSteps, stepLabels }: ProgressBarProps) {
  const percentage = (currentStep / totalSteps) * 100

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-900">
          Прогресс создания контента
        </h2>
        <span className="text-sm font-medium text-primary-600">
          {currentStep} / {totalSteps} шагов
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative w-full h-3 bg-gray-200 rounded-full overflow-hidden mb-4">
        <div
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-primary-500 to-primary-600 transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        >
          <div className="absolute inset-0 bg-white opacity-20 animate-pulse"></div>
        </div>
      </div>

      {/* Step indicators */}
      <div className="grid grid-cols-8 gap-2">
        {stepLabels.map((label, index) => {
          const stepNumber = index + 1
          const isCompleted = stepNumber < currentStep
          const isCurrent = stepNumber === currentStep

          return (
            <div key={index} className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold mb-1 transition-all duration-300 ${
                  isCompleted
                    ? 'bg-green-500 text-white shadow-md'
                    : isCurrent
                    ? 'bg-primary-600 text-white shadow-lg ring-4 ring-primary-200 animate-pulse'
                    : 'bg-gray-300 text-gray-600'
                }`}
              >
                {isCompleted ? '✓' : stepNumber}
              </div>
              <span
                className={`text-xs text-center leading-tight ${
                  isCurrent ? 'text-primary-600 font-semibold' : 'text-gray-500'
                }`}
              >
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
