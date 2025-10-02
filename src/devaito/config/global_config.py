import os

from dotenv import load_dotenv


class GlobalConfig:
    def __init__(self):
        load_dotenv()
        self.AGENT_CLIENT = os.getenv("AGENT_CLIENT")
