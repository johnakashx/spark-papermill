# spark-papermill

Run Jupyter notebooks with a pre-initialized `SparkSession` — no Spark setup code required in your notebooks.

`spark-papermill` wraps [papermill](https://papermill.readthedocs.io/) and automatically injects a bootstrap cell that creates a `SparkSession` before your notebook executes. It supports **Spark Connect** (`sc://`), **classic Spark master** (`spark://`), and **local mode** — detected automatically from a single environment variable.

---

## Requirements

- Python >= 3.9
- Java 8 or 11 (required by PySpark)
- PySpark >= 3.4

---

## Installation

### Classic Spark (`spark://` or `local[*]`)

```bash
pip install spark-papermill
```

### Spark Connect (`sc://`)

```bash
pip install spark-papermill[connect]
```

### From source

```bash
git clone https://github.com/your-org/spark-papermill.git
cd spark-papermill
pip install -e .

# or with Spark Connect support
pip install -e ".[connect]"
```

---

## Configuration

Set a single environment variable before running — `spark-papermill` detects the mode from the URL prefix automatically.

| Mode | Example |
|---|---|
| Spark Connect | `export SPARK_ENDPOINT_URL=sc://host:15002` |
| Classic master | `export SPARK_ENDPOINT_URL=spark://host:7077` |
| Local | `export SPARK_ENDPOINT_URL=local[*]` |
| YARN | `export SPARK_ENDPOINT_URL=yarn` |

Optionally set the Spark application name:

```bash
export SPARK_APP_NAME=my-notebook-job
```

---

## Usage

### CLI

```bash
spark-papermill INPUT OUTPUT [OPTIONS]
```

**Arguments**

| Argument | Description |
|---|---|
| `INPUT` | Path to the input notebook |
| `OUTPUT` | Path to save the executed notebook |

**Options**

| Flag | Description |
|---|---|
| `-p NAME VALUE` | Pass a typed parameter (infers int, float, bool, string) |
| `-r NAME VALUE` | Pass a raw string parameter (no type inference) |
| `-k KERNEL` | Jupyter kernel name to use |

### Examples

**Local mode**
```bash
export SPARK_ENDPOINT_URL=local[*]
spark-papermill analysis.ipynb output.ipynb
```

**With parameters**
```bash
export SPARK_ENDPOINT_URL=local[*]
spark-papermill analysis.ipynb output.ipynb \
  -p run_id abc123 \
  -p date 2026-09-05 \
  -p limit 1000
```

**Spark Connect remote server**
```bash
export SPARK_ENDPOINT_URL=sc://88.208.224.248:15002
export SPARK_APP_NAME=my-etl-job
spark-papermill etl.ipynb output.ipynb -p warehouse cn_group_1
```

**Classic Spark master**
```bash
export SPARK_ENDPOINT_URL=spark://88.208.224.248:7077
spark-papermill etl.ipynb output.ipynb
```

**Custom kernel**
```bash
spark-papermill analysis.ipynb output.ipynb -k python3
```

---

## How it works

You do not need any Spark setup code in your notebook. Just use `spark` directly:

```python
# your notebook cell — no imports needed
df = spark.sql("SELECT * FROM my_table")
df.show()
```

`spark-papermill` prepends this bootstrap cell automatically before execution:

```python
from spark_papermill.spark import initialize_spark
spark = initialize_spark()
```

The original notebook file is never modified. Execution flow:

1. Read your notebook
2. Prepend the bootstrap cell into a temporary copy
3. Run papermill on the temporary copy
4. Write the executed notebook to `OUTPUT`
5. Delete the temporary copy

---

## Using in an Airflow DAG (KubernetesPodOperator)

```python
env_vars={
    "SPARK_ENDPOINT_URL": "sc://88.208.224.248:15002",
    "SPARK_APP_NAME": "{{ dag.dag_id }}",
},
arguments=[
    "set -e && "
    # ... az download-batch staging ...
    "spark-papermill Untitled.ipynb output.ipynb -p run_id '{{ run_id }}'"
]
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SPARK_ENDPOINT_URL` | Yes | — | Spark endpoint. Prefix determines mode (`sc://`, `spark://`, `local[*]`, etc.) |
| `SPARK_APP_NAME` | No | `spark-papermill` | Spark application name shown in the Spark UI |

---

## Troubleshooting

**`SPARK_ENDPOINT_URL is not set`**
Set the environment variable before running:
```bash
export SPARK_ENDPOINT_URL=local[*]
```

**`SparkContext has been stopped and cannot be restarted`**
You called `spark.stop()` earlier in the same kernel session. Restart the kernel — do not call `spark.stop()` during interactive development.

**`ParseException: Syntax error at or near end of input (pos 0)`**
The SQL string passed to `spark.sql()` is empty. Check that your notebook parameter cell is correctly tagged and that `-p` values are being passed.

**Version mismatch warning / `SQL_CONF_NOT_FOUND`**
Your PySpark client version does not match the Spark Connect server version. Pin them to match:
```bash
pip install pyspark[connect]==<server-version>
```
Check the server version at `http://your-host:8080`.

---

## Running a Spark Connect Server

A Docker Compose setup is included for running your own Spark Connect server.

```bash
# Set your server's public IP
export SPARK_PUBLIC_DNS=88.208.224.248

docker compose up --build -d
```

Then connect from any client:

```bash
export SPARK_ENDPOINT_URL=sc://88.208.224.248:15002
spark-papermill notebook.ipynb output.ipynb
```

Spark UI is available at `http://88.208.224.248:8080`.
