import os
import re
import yaml


def _substitute_env_vars(value):
    """
    Recursively substitute environment variables in config values.
    Supports ${VAR_NAME} syntax.

    Args:
        value: Config value (can be str, dict, list, or other types)

    Returns:
        Value with environment variables substituted
    """
    if isinstance(value, str):
        # Match ${VAR_NAME} pattern and replace with environment variable
        def replacer(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Return original if not found
        return re.sub(r'\$\{([^}]+)\}', replacer, value)
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    else:
        return value


def load_config(config_file: str) -> dict:
    """
    Load and parse a YAML configuration file with environment variable substitution.
    Supports ${VAR_NAME} syntax for referencing environment variables.

    Args:
        config_file (str): Path to the YAML configuration file.
    Returns:
        dict: Parsed configuration as a dictionary with env vars substituted.
    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the configuration file is empty or contains invalid YAML.
    """
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        if not config:
            raise ValueError("Configuration file is empty or invalid.")
        # Substitute environment variables
        config = _substitute_env_vars(config)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {str(e)}")
