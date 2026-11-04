from django.db import Error, connection


def is_database_reachable():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Error:
        return False
    return True
