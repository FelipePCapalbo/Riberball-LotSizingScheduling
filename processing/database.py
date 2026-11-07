import os
import sqlite3

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(ROOT_DIR, 'database', 'riberball.sqlite'))

SCHEMA = '''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    type TEXT NOT NULL,
    unit_cost REAL NOT NULL,
    sale_price REAL NOT NULL,
    min_lot_kg REAL NOT NULL,
    is_mts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sku_classes (
    product TEXT NOT NULL,
    color TEXT NOT NULL,
    is_mts INTEGER NOT NULL,
    PRIMARY KEY (product, color)
);

CREATE TABLE IF NOT EXISTS machines (
    machine TEXT PRIMARY KEY,
    is_active INTEGER NOT NULL,
    setup_hourly_cost REAL NOT NULL,
    color_sides INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS productivity (
    product TEXT NOT NULL,
    machine TEXT NOT NULL,
    kg_per_hour REAL NOT NULL,
    PRIMARY KEY (product, machine)
);

CREATE TABLE IF NOT EXISTS form_setup (
    from_product TEXT NOT NULL,
    to_product TEXT NOT NULL,
    hours REAL NOT NULL,
    PRIMARY KEY (from_product, to_product)
);

CREATE TABLE IF NOT EXISTS color_setup (
    from_color TEXT NOT NULL,
    to_color TEXT NOT NULL,
    hours REAL NOT NULL,
    PRIMARY KEY (from_color, to_color)
);

CREATE TABLE IF NOT EXISTS availability (
    week TEXT NOT NULL,
    machine TEXT NOT NULL,
    availability REAL NOT NULL,
    PRIMARY KEY (week, machine)
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    sheets TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forecast (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    product TEXT NOT NULL,
    week TEXT NOT NULL,
    quantity REAL NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, product, week, source)
);

CREATE TABLE IF NOT EXISTS forecast_accuracy (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    product TEXT NOT NULL,
    mape REAL NOT NULL,
    PRIMARY KEY (snapshot_id, product)
);

CREATE TABLE IF NOT EXISTS color_mix (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    product TEXT NOT NULL,
    color TEXT NOT NULL,
    share REAL NOT NULL,
    PRIMARY KEY (snapshot_id, product, color)
);

CREATE TABLE IF NOT EXISTS orders (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    order_id TEXT NOT NULL,
    customer TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, order_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    order_id TEXT NOT NULL,
    product TEXT NOT NULL,
    color TEXT NOT NULL,
    quantity REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS product_stock (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    product TEXT NOT NULL,
    quantity REAL NOT NULL,
    PRIMARY KEY (snapshot_id, product)
);

CREATE TABLE IF NOT EXISTS sku_stock (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    product TEXT NOT NULL,
    color TEXT NOT NULL,
    quantity REAL NOT NULL,
    PRIMARY KEY (snapshot_id, product, color)
);

CREATE TABLE IF NOT EXISTS initial_form (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots (snapshot_id),
    machine TEXT NOT NULL,
    product TEXT NOT NULL,
    color TEXT,
    color_side_2 TEXT,
    PRIMARY KEY (snapshot_id, machine)
);

CREATE TABLE IF NOT EXISTS uploads (
    upload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    snapshot_id INTEGER REFERENCES snapshots (snapshot_id)
);

CREATE TABLE IF NOT EXISTS master_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER NOT NULL REFERENCES uploads (upload_id),
    table_name TEXT NOT NULL,
    record_key TEXT NOT NULL,
    change_type TEXT NOT NULL,
    old_values TEXT,
    new_values TEXT,
    decision TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    label TEXT NOT NULL,
    snapshot_id INTEGER REFERENCES snapshots (snapshot_id),
    source TEXT NOT NULL,
    settings TEXT NOT NULL,
    weekly_status TEXT NOT NULL,
    weekly_duration REAL NOT NULL,
    weekly_result TEXT NOT NULL,
    daily_status TEXT,
    daily_duration REAL,
    daily_result TEXT
);
'''

MASTER_TABLES = {
    'products': {
        'keys': ['product'],
        'defaults': {'model': '', 'type': '', 'unit_cost': 0.0, 'sale_price': 0.0, 'min_lot_kg': 0.0, 'is_mts': 1},
    },
    'sku_classes': {
        'keys': ['product', 'color'],
        'defaults': {'is_mts': 1},
    },
    'machines': {
        'keys': ['machine'],
        'defaults': {'is_active': 1, 'setup_hourly_cost': 250.0, 'color_sides': 1},
    },
    'productivity': {
        'keys': ['product', 'machine'],
        'defaults': {'kg_per_hour': 0.0},
    },
    'form_setup': {
        'keys': ['from_product', 'to_product'],
        'defaults': {'hours': 0.0},
    },
    'color_setup': {
        'keys': ['from_color', 'to_color'],
        'defaults': {'hours': 0.0},
    },
    'availability': {
        'keys': ['week', 'machine'],
        'defaults': {'availability': 1.0},
    },
}

ADDED_COLUMNS = [
    ['machines', 'color_sides', 'INTEGER NOT NULL DEFAULT 1'],
    ['initial_form', 'color_side_2', 'TEXT'],
]

SNAPSHOT_TABLES = ['forecast', 'forecast_accuracy', 'color_mix', 'orders', 'order_items',
                   'product_stock', 'sku_stock', 'initial_form']


def connect_database():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.executescript(SCHEMA)
    for list_added in ADDED_COLUMNS:
        list_existing_columns = []
        for row in connection.execute(f'PRAGMA table_info({list_added[0]})'):
            list_existing_columns.append(row['name'])
        if list_added[1] not in list_existing_columns:
            connection.execute(f'ALTER TABLE {list_added[0]} ADD COLUMN {list_added[1]} {list_added[2]}')
    return connection


def fetch_rows(connection, str_query, tuple_parameters):
    list_rows = []
    for row in connection.execute(str_query, tuple_parameters):
        dict_row = {}
        for str_column in row.keys():
            dict_row[str_column] = row[str_column]
        list_rows.append(dict_row)
    return list_rows
