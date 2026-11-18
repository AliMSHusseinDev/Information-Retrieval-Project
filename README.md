# Information Retrieval Project

## Run the Windows x64 ZIP

1. Extract the entire ZIP to a short local path such as `C:\IR`. Allow about 1 GB of free space for the extracted files.
2. Double-click `Launch_IR.bat`. The portable distribution includes Python, Java, PySpark, Flask and Waitress. It runs offline. Keep the console open during the demo.
3. Click **Import Documents**. Choose one or more UTF-8 text files. Use **Choose files…** again to add documents from another folder, then **Import selection**.
4. When Spark finishes, the ready screen stays visible for two seconds. Explore the index, matrices, search, query mathematics and exports. Open the original launcher address for an empty workspace. Importing from an active collection replaces it after success.
5. Press Enter in the launcher console to stop the app. Collections live in memory for the current run.

The supplied Fall 2026 dataset is in `data/`. Healthcare, Technology, Education and Business each contain ten documents. For a mixed demo, choose Healthcare’s `d1.txt` and Business’s `d1.txt`, then search for **patient care** and **customer service**. Both files keep their original names. Matrix columns have unique document IDs. The overview lists the ID and filename together.

## Run from source on Linux, macOS or Windows

Use Python 3.12 and Java 17 or 21. On Windows, `Launch_IR.bat` uses the bundled runtime when present, or creates a virtual environment with the full requirements. On Linux or macOS:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python launcher.py --no-browser --headless
```

Open the local address printed by the launcher. Each import runs real Spark positional indexing. TF-IDF, normalized vectors, exact phrase matching, Boolean AND / AND NOT and cosine rankings use the selected files. Suggested queries and their exports use the current vocabulary. Terms are lowercased and split on whitespace. With one document all IDF values are zero, so exact matches have zero cosine scores.

The offline reference exports in `outputs/` correspond to the Technology assignment. To rebuild them from a development environment, run `python run_spark.py`. The web app creates its own exports during import.

## Validation

Run `python validate.py` with the full dependencies installed. Run `python tests/launcher_smoke.py` with the launcher stopped. For browser validation, start the app and run `python tests/browser_smoke.py` with Playwright 1.62.0 and Chromium. Set `IR_BROWSER_EXECUTABLE` for a system Chromium. The browser test imports the Technology collection, checks the six pages, and then mixes files from two domains. It writes screenshots under `screenshots/`.

The original project specification and theory guides are in `docs/`.
