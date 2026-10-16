use duckdb::{Connection, params};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let dir = tempfile::tempdir()?;
    let database = dir.path().join("query.duckdb");
    let parquet = dir.path().join("query.parquet");
    {
        let mut db = Connection::open(&database)?;
        let version: String = db.query_row("SELECT version()", [], |r| r.get(0))?;
        assert_eq!(version, "v1.5.5");
        db.execute_batch("CREATE TABLE items(id INTEGER, label VARCHAR)")?;
        db.execute("INSERT INTO items VALUES (?, ?)", params![42_i32, "DuckDB"])?;
        {
            let tx = db.transaction()?;
            tx.execute("INSERT INTO items VALUES (?, ?)", params![99_i32, "rollback"])?;
            tx.rollback()?;
        }
        let value: i32 = db.query_row("SELECT sum(id)::INTEGER FROM items", [], |r| r.get(0))?;
        assert_eq!(value, 42);
        let mut stmt = db.prepare("SELECT id, label FROM items")?;
        let rows: usize = stmt.query_arrow([])?.map(|batch| batch.num_rows()).sum();
        assert_eq!(rows, 1);
        let path = parquet.to_str().ok_or("non-UTF8 temporary path")?.replace('\'', "''");
        db.execute_batch(&format!("COPY items TO '{path}' (FORMAT PARQUET)"))?;
        let result: (i32, String) = db.query_row(
            "SELECT id, label FROM read_parquet(?)",
            [parquet.to_str().unwrap()],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )?;
        assert_eq!(result, (42, "DuckDB".to_owned()));
    }
    let db = Connection::open(&database)?;
    let row: (i32, String) = db.query_row("SELECT id, label FROM items", [], |r| Ok((r.get(0)?, r.get(1)?)))?;
    assert_eq!(row, (42, "DuckDB".to_owned()));
    println!("DuckDB v1.5.5: parameters, Arrow, rollback, Parquet and reopen passed");
    Ok(())
}
