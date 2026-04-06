import json
import logging, time, os
from config import Config
from data_loader import write_json


class Logger(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level=logging.INFO)
        self.log_dir = Config.log_dir + '/log_' + time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime(time.time())) + '/'
        self.log_current = self.log_dir + 'current.json'
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.handler = logging.FileHandler(self.log_dir + 'fuzz.log', encoding='utf-8')
        self.handler.setLevel(logging.INFO)
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(self.formatter)

        self.console = logging.StreamHandler()
        self.console.setLevel(logging.INFO)

        self.logger.addHandler(self.handler)
        self.logger.addHandler(self.console)

    def get_logger(self):
        return self.logger

    def get_handler(self):
        return self.handler

    def get_formatter(self):
        return self.formatter

    def get_console(self):
        return self.console

    def save_current(self, data):
        with open(self.log_current, 'w+', encoding='utf-8') as f:
            file = f.read()
            if len(file) > 0:
                file_data = json.loads(file)
            else:
                file_data = list()
        file_data.append(data)
        write_json(self.log_current, file_data)
