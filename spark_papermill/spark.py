import os
import warnings
from pyspark import SparkContext
from pyspark.sql import SparkSession


def initialize_spark() -> SparkSession:
    """
    Initializes and returns a SparkSession from a single env var: SPARK_ENDPOINT_URL.

    Routing:
        sc://    -> SparkSession.builder.remote()  (Spark Connect)
        spark:// -> SparkSession.builder.master()  (classic)
        local*   -> SparkSession.builder.master()  (local mode)
        yarn, k8s://, etc -> SparkSession.builder.master()
    """
    app_name = os.environ.get("SPARK_APP_NAME", "spark-papermill")
    endpoint = os.environ.get("SPARK_ENDPOINT_URL")

    if not endpoint:
        raise EnvironmentError(
            "SPARK_ENDPOINT_URL is not set. "
            "Examples:\n"
            "  Spark Connect : export SPARK_ENDPOINT_URL=sc://host:15002\n"
            "  Classic master: export SPARK_ENDPOINT_URL=spark://host:7077\n"
            "  Local mode    : export SPARK_ENDPOINT_URL=local[*]"
        )

    builder = SparkSession.builder.appName(app_name)

    if endpoint.startswith("sc://"):
        spark = builder.remote(endpoint).getOrCreate()
    else:
        # Guard against stopped SparkContext (classic mode only)
        sc = SparkContext._active_spark_context
        if sc is not None and sc._jsc is None:
            raise RuntimeError(
                "SparkContext has been stopped and cannot be restarted in the same process. "
                "Restart your kernel and avoid calling spark.stop() during development."
            )
        spark = builder.master(endpoint).getOrCreate()

    return spark
