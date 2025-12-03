import asyncio

import typer


app = typer.Typer(help="Intelligent Recommend Agent Application")


@app.command()
def terminal():
    from cmds.terminal import main

    return asyncio.run(main())


@app.command()
def web_terminal():
    from cmds.web_terminal import main

    return asyncio.run(main())


if __name__ == "__main__":
    app()