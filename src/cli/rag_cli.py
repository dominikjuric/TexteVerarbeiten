#!/usr/bin/env python3

"""Interactive CLI for the simple RAG session."""

import argparse
import textwrap

from src.rag import DEFAULT_MODEL, SimpleRAGSession


def _print_banner(model_name: str) -> None:
    print("Willkommen zur RAG-Konsole! 🎓")
    print(f"Aktuelles LLM: {model_name}")
    print("Tippe deine Frage und drücke Enter. Verfügbare Befehle:")
    print("  /history  → zeigt bisherige Fragen & Antworten")
    print("  /clear    → löscht den Gesprächskontext")
    print("  /quit     → beendet die Sitzung")


def _print_sources(sources) -> None:
    if not sources:
        print("Keine Quellen gefunden.")
        return

    print("Quellen:")
    for idx, source in enumerate(sources, start=1):
        label = source.display_label()
        snippet = textwrap.shorten(source.document.replace("\n", " "), width=180, placeholder=" …")
        print(f"  [{idx}] {label}")
        print(f"       {snippet}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Starte eine interaktive RAG-Sitzung")
    parser.add_argument("--k", type=int, default=5, help="Anzahl der Kontext-Chunks pro Frage")
    parser.add_argument("--model", default=None, help="Optional: alternatives OpenAI-Chatmodell")
    parser.add_argument("--temperature", type=float, default=0.0, help="Antwort-Kreativität des Modells")
    parser.add_argument("--history-limit", type=int, default=10, help="Maximale Anzahl gemerkter Gesprächsrunden")
    parser.add_argument("--persist-path", default=".chroma", help="Pfad zum ChromaDB-Verzeichnis")
    parser.add_argument("--collection", default="papers", help="Name der zu nutzenden Collection")
    parser.add_argument("--embedding-model", default=None, help="Alternatives SentenceTransformer-Modell")
    parser.add_argument("--api-key", default=None, help="OpenAI API Key (überschreibt .env)")
    args = parser.parse_args()

    session = SimpleRAGSession(
        chat_model=args.model or DEFAULT_MODEL,
        temperature=args.temperature,
        history_limit=args.history_limit,
        persist_path=args.persist_path,
        collection_name=args.collection,
        embedding_model=args.embedding_model,
        api_key=args.api_key,
    )

    _print_banner(session.chat_model)

    while True:
        try:
            question = input("Du: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBeende Sitzung.")
            break

        if not question:
            continue

        lowered = question.lower()
        if lowered in {"/quit", "quit", "exit"}:
            print("Auf Wiedersehen!")
            break
        if lowered == "/clear":
            session.clear_history()
            print("🧹 Gesprächshistorie gelöscht.")
            continue
        if lowered == "/history":
            history = session.get_history()
            if not history:
                print("Noch keine Einträge vorhanden.")
            else:
                for idx, turn in enumerate(history, start=1):
                    print(f"\n[{idx}] Frage: {turn.question}")
                    print(f"      Antwort: {turn.answer}")
            continue

        result = session.ask(question, k=args.k)
        print(f"\nAssistent: {result['answer']}\n")
        _print_sources(result["sources"])


if __name__ == "__main__":
    main()

