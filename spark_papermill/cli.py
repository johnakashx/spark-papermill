import argparse
import os
import sys
import tempfile
import nbformat
import papermill as pm

def _parse_value(val: str):
    """
    Helper to cast parameter values from strings (mirroring Papermill CLI behavior).
    """
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val

def main():
    parser = argparse.ArgumentParser(description="Run Jupyter notebooks with a pre-initialized SparkSession")
    parser.add_argument("INPUT", help="Path to the original input notebook")
    parser.add_argument("OUTPUT", help="Path to save the executed notebook")
    parser.add_argument("-k", "--kernel", help="Jupyter kernel to use")
    
    # Papermill parameter arguments
    parser.add_argument(
        "-p", "--parameter",
        nargs=2,
        action="append",
        metavar=("NAME", "VALUE"),
        help="Set a parameter for the notebook (infers int, float, bool, or string). Can be used multiple times."
    )
    parser.add_argument(
        "-r", "--parameters_raw",
        nargs=2,
        action="append",
        metavar=("NAME", "VALUE"),
        help="Set a raw string parameter for the notebook (skips type inference). Can be used multiple times."
    )
    
    args = parser.parse_args()
    input_path = args.INPUT
    output_path = args.OUTPUT

    if not os.path.exists(input_path):
        sys.exit(f"Error: Input notebook '{input_path}' does not exist.")

    # Build parameters dictionary
    parameters = {}
    if args.parameter:
        for name, value in args.parameter:
            parameters[name] = _parse_value(value)
    
    if args.parameters_raw:
        for name, value in args.parameters_raw:
            parameters[name] = value

    # 1. Read the user's notebook safely
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        sys.exit(f"Error: Failed to parse input notebook '{input_path}'. Details: {e}")

    # 2. Insert the bootstrap cell at the beginning (index 0)
    bootstrap_code = (
        "from spark_papermill.spark import initialize_spark\n"
        "spark = initialize_spark()"
    )
    bootstrap_cell = nbformat.v4.new_code_cell(source=bootstrap_code)
    nb.cells.insert(0, bootstrap_cell)

    # 3. Create a temporary file to save the modified notebook
    fd, temp_path = tempfile.mkstemp(suffix=".ipynb")
    os.close(fd) 

    try:
        # Write modified notebook to the temporary path
        with open(temp_path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)

        # 4. & 5. Run Papermill on the temp notebook and write to the requested OUTPUT
        print(f"Starting execution of '{input_path}'...")
        if parameters:
            print(f"Passing parameters: {parameters}")
        print("Injecting Spark bootstrap cell...")
        
        pm_kwargs = {}
        if args.kernel:
            pm_kwargs['kernel_name'] = args.kernel
        if parameters:
            pm_kwargs['parameters'] = parameters

        pm.execute_notebook(
            input_path=temp_path,
            output_path=output_path,
            **pm_kwargs
        )
        print(f"Success! Executed notebook saved to: {output_path}")

    except pm.exceptions.PapermillExecutionError as e:
        print(f"\nPapermill Execution Failed:\n{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred during execution:\n{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # 6. Clean up: Delete the temporary notebook
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    main()