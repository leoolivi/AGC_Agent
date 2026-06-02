interface ConfidenceIndicatorProps {
  score: number;
}

export function ConfidenceIndicator({ score }: ConfidenceIndicatorProps) {
  let label: string;
  let color: string;

  if (score >= 0.85) {
    label = "Estratto";
    color = "text-green-700 bg-green-50";
  } else if (score >= 0.60) {
    label = "Inferito";
    color = "text-amber-700 bg-amber-50";
  } else {
    label = "Suggerito";
    color = "text-gray-600 bg-gray-50";
  }

  return (
    <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded mt-1 ${color}`}>
      {label} ({Math.round(score * 100)}%)
    </span>
  );
}
