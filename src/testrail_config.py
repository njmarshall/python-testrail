import configparser


def get_testrail_config():
    config = configparser.ConfigParser()
    config.read('testrail.ini')  # Path to your configuration file

    section = 'TestRail'
    base_url = config.get(section, 'base_url')
    username = config.get(section, 'username')
    api_key = config.get(section, 'api_key')

    return base_url, username, api_key
