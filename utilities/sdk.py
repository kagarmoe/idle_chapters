from pydantic import BaseModel, ValidationError
import typer
import json
from pathlib import Path

# Define the Typer app
app = typer.Typer()

# Define a Pydantic schema
class PlayerSchema(BaseModel):
    name: str
    level: int
    inventory: list[str]

# Command to validate a JSON file against the schema
@app.command()
def validate_json(file_path: str):
    """Validate against the Player schema."""
    try:
        # Read the JSON file
        file = Path(file_path)
        if not file.exists():
            typer.echo(f"File not found: {file_path}")
            raise typer.Exit(code=1)

        with file.open("r") as f:
            data = json.load(f)

        # Validate the data
        player = PlayerSchema(**data)
        typer.echo("Validation successful!")
        typer.echo(player.json(indent=4))

    except ValidationError as e:
        typer.echo("Validation failed:")
        typer.echo(e.json(indent=4))
        raise typer.Exit(code=1)

    except json.JSONDecodeError:
        typer.echo("Invalid JSON file.")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()