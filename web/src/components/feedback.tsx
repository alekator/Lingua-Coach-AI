type Props = {
  text: string;
};

export function LoadingState({ text }: Props) {
  return <p className="status loading">{text}</p>;
}

export function EmptyState({ text }: Props) {
  return <p className="status empty">{text}</p>;
}

export function ErrorState({ text }: Props) {
  return <p className="status error">{text}</p>;
}
