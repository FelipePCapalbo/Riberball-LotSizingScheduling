import json

from processing.data import SNAPSHOT_SHEETS
from processing.database import connect_database, fetch_rows


def get_active_snapshot_id():
    connection = connect_database()
    list_rows = fetch_rows(connection, "SELECT value FROM app_state WHERE key = 'active_snapshot_id'", ())
    connection.close()
    int_snapshot_id = None
    if list_rows:
        int_snapshot_id = json.loads(list_rows[0]['value'])
    return int_snapshot_id


def set_active_snapshot_id(connection, int_snapshot_id):
    connection.execute(
        "INSERT INTO app_state (key, value) VALUES ('active_snapshot_id', ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (json.dumps(int_snapshot_id),))


def get_upload_review(int_upload_id):
    connection = connect_database()
    list_uploads = fetch_rows(connection, 'SELECT * FROM uploads WHERE upload_id = ?', (int_upload_id,))
    list_changes = fetch_rows(connection, 'SELECT * FROM master_changes WHERE upload_id = ? ORDER BY change_id',
                              (int_upload_id,))
    connection.close()
    dict_review = None
    if list_uploads:
        dict_upload = list_uploads[0]
        dict_payload = json.loads(dict_upload['payload'])
        list_snapshot_sheets = []
        for str_sheet in SNAPSHOT_SHEETS:
            if str_sheet in dict_payload['sheets']:
                list_snapshot_sheets.append(str_sheet)
        dict_insert_counts = {}
        list_conflicts = []
        for dict_change in list_changes:
            if dict_change['change_type'] == 'insert':
                if dict_change['table_name'] not in dict_insert_counts:
                    dict_insert_counts[dict_change['table_name']] = 0
                dict_insert_counts[dict_change['table_name']] += 1
            else:
                dict_old_values = None
                if dict_change['old_values'] is not None:
                    dict_old_values = json.loads(dict_change['old_values'])
                dict_new_values = None
                if dict_change['new_values'] is not None:
                    dict_new_values = json.loads(dict_change['new_values'])
                list_conflicts.append({
                    'change_id': dict_change['change_id'],
                    'table_name': dict_change['table_name'],
                    'record_key': json.loads(dict_change['record_key']),
                    'change_type': dict_change['change_type'],
                    'old_values': dict_old_values,
                    'new_values': dict_new_values,
                    'decision': dict_change['decision'],
                })
        dict_review = {
            'upload_id': dict_upload['upload_id'],
            'created_at': dict_upload['created_at'],
            'source_file': dict_upload['source_file'],
            'status': dict_upload['status'],
            'snapshot_id': dict_upload['snapshot_id'],
            'snapshot_sheets': list_snapshot_sheets,
            'insert_counts': dict_insert_counts,
            'conflicts': list_conflicts,
        }
    return dict_review
