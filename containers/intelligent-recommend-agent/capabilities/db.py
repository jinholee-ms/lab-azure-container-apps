from langchain_community.utilities import SQLDatabase
import pandas as pd
from sqlalchemy import create_engine
import sqlite3


class ReadOnlySQLDatabase(SQLDatabase):
    def __init__(self, assets, *args, **kwargs):
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        for filename, tablename in assets:
            data = pd.read_csv(filename)
            data.columns = [c.strip().replace(" ", "_") for c in data.columns]
            data.to_sql(tablename, self.connection, if_exists="replace", index=False)
        self.engine = create_engine("sqlite+pysqlite://", creator=lambda: self.connection)

        super().__init__(self.engine, *args, **kwargs)

    def run(self, command: str, *args, **kwargs) -> str:
        return super().run(command.strip(), *args, **kwargs)
