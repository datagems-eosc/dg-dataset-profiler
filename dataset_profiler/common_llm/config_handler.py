import yaml


def load_config(config_file: str) -> dict:
    """
    Load and parse a YAML configuration file.
    Args:
        config_file (str): Path to the YAML configuration file.
    Returns:
        dict: Parsed configuration as a dictionary.
    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the configuration file is empty or contains invalid YAML.
    """
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        if not config:
            raise ValueError("Configuration file is empty or invalid.")
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {str(e)}")
