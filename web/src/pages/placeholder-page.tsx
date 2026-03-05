type Props = {
  title: string;
  description: string;
};

export function PlaceholderPage({ title, description }: Props) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}
