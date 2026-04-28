from __future__ import annotations

import argparse

from app.nlu import convert_rasa_nlu, save_model, train_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train lightweight NLU model from Rasa NLU YAML")
    parser.add_argument("--input", required=True, help="Path to Rasa-style nlu.yml")
    parser.add_argument("--output", required=True, help="Path to output joblib model")
    args = parser.parse_args()

    samples, known_values = convert_rasa_nlu(args.input)
    if not samples:
        raise SystemExit("No training samples found")

    model = train_model(samples=samples, known_values=known_values)
    save_model(model, args.output)
    print(f"Model saved to {args.output} with {len(samples)} samples")


if __name__ == "__main__":
    main()
