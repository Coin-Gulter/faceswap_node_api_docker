import uuid
import configparser

def generate_unique_task_id(db_model):
    """
    Generates a unique task_id string using a UUIDv4 format.

    Returns:
        str: A unique task_id string.
    """

    while True:
        task_id = str(uuid.uuid4())

        # Check for uniqueness in the database
        if db_model.objects.filter(task_id=task_id).exists():
            continue  # Try again if already exists

        return task_id
    

def load_config(config_path:str, parameters:list, section:str = 'main'):
    """
    Reads and parses the configuration file.

        args:
            config_path (str): Path to the config file
            parameters (list): List of name of parameters
            section (str) = 'main' : Section in the config file where you want to get parameters
        
        return:
            dict: Dictionary of parameters and values
            None: If there is no selected section in .cnf file or no file
    """

    config = configparser.ConfigParser()
    config.read(config_path)

    config_dict = {}
    
    for p in parameters:
        try:
            config_dict[p] = config.get(section, p)
        except configparser.NoSectionError:
            return None
        except configparser.NoOptionError:
            config_dict[p] = None

    return config_dict

