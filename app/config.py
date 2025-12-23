import os

class Config:
    """
    Centraliza as configurações e caminhos do projeto.
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'CSV')
    
    # Constantes de Negócio
    HIGH_SETUP_MACHINES = ['11', '14']
    DEFAULT_SETUP_TIME_HIGH = 7.0 
    DEFAULT_SETUP_TIME_LOW = 3.0
    BACKLOG_PENALTY_FACTOR = 0.1
    
    @staticmethod
    def get_file_path(filename):
        return os.path.join(Config.DATA_DIR, filename)

