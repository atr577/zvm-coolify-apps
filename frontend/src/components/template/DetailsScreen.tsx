import { ConfigureSection } from './ConfigureSection'

interface DetailsScreenProps {
  projectId: number
}

export function DetailsScreen({ projectId }: DetailsScreenProps) {
  return <ConfigureSection projectId={projectId} showProjectSettings />
}
