import os

class Config:
    """
    Centraliza as configurações e caminhos do projeto.
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_FILE = os.path.join(BASE_DIR, '..', 'data', 'inputs.xlsx')

    # Constantes de Negócio
    HIGH_SETUP_MACHINES = ['11', '14']
    DEFAULT_SETUP_TIME_HIGH = 7.0
    DEFAULT_SETUP_TIME_LOW = 3.0

