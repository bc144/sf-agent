import os
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv
from pydantic import ValidationError
from pydantic_ai import Agent
from rich.console import Console
from rich.table import Table

try:  # pragma: no cover - import shim for script execution
    from .models import Constraints, ProductCard, SearchRequest, SearchResponse
except ImportError:  # pragma: no cover
    from models import Constraints, ProductCard, SearchRequest, SearchResponse  # type: ignore


# Load environment variables from .env file in parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

API_URL = os.getenv("API_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("PYDANTIC_AGENT_MODEL", "gpt-4o-mini")


console = Console()


def _call_search_api(query: str, constraints: Optional[Constraints], k: int) -> List[ProductCard]:
    payload = SearchRequest(query=query, constraints=constraints or Constraints(), k=k).model_dump()
    response = requests.post(f"{API_URL}/search", json=payload, timeout=30)
    response.raise_for_status()
    try:
        data = SearchResponse.model_validate(response.json())
    except ValidationError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Invalid response from API: {exc}")
    return data.items


agent = Agent[None, List[ProductCard]](
    model=f"openai:{MODEL_NAME}",
    system_prompt=(
        "You are a shopping agent. ALWAYS use tools; do not invent SKUs. "
        "Return 3–6 options with a short 'why'. If results are scarce, suggest relaxing color/price/size."
    ),
)


@agent.tool
def search_products(query: str, constraints: Optional[Constraints] = None, k: int = 6) -> List[ProductCard]:
    """Search for products using the FastAPI endpoint and return the best matches."""

    items = _call_search_api(query=query, constraints=constraints, k=k)
    return items[: min(max(3, k), 6)]


def _render_products(products: List[ProductCard]) -> None:
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Title")
    table.add_column("Price")
    table.add_column("Sizes")
    table.add_column("Why")

    for item in products:
        sizes = ", ".join(item.sizes) if item.sizes else "-"
        table.add_row(item.title, f"${item.price:.2f}", sizes, item.why or "")

    console.print(table)


def main() -> None:
    console.print("[bold]Shopping agent ready.[/] Type 'exit' to quit.")
    while True:
        prompt = input("Query> ").strip()
        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            console.print("Goodbye!")
            break

        try:
            result = agent.run_sync(prompt)
        except Exception as exc:  # pragma: no cover - runtime diagnostics
            console.print(f"[red]Error: {exc}[/]")
            continue

        products = result.data if hasattr(result, "data") else []
        if not products:
            console.print("[yellow]No products found. Try relaxing filters.[/]")
            continue

        _render_products(products)


if __name__ == "__main__":
    main()
