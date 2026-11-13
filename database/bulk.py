from database import connection


def insert(conn, df, table, schema="dbo"):
    if df.empty:
        return 0
    if connection.FAST:
        df.to_sql(table, conn, schema=schema, if_exists="append", index=False, chunksize=20000)
    else:
        size = max(1, min(1000, 2000 // len(df.columns)))
        df.to_sql(table, conn, schema=schema, if_exists="append", index=False, chunksize=size, method="multi")
    return len(df)