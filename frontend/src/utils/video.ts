export function formatMetricNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  return num.toString()
}

export function getStepLabel(stepType: string): string {
  const map: Record<string, string> = {
    story: 'Story',
    description: 'Description',
    prompt: 'Image Prompt',
    image: 'Image',
    scenario: 'Scenario',
    video: 'Video',
    audio: 'Audio',
    adaptation: 'Adaptation',
    publishing: 'Publishing'
  }
  return map[stepType] || stepType
}
