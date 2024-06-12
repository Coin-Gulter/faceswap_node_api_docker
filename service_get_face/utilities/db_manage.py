import pymysql
import ssl
from utilities import utils
import os
import time

DATA_PATH = os.environ.get('data_path', 'data/')

class MySQLDB:
    MAX_RETRIES = 5
    RETRY_DELAY = 1

    def __init__(self, mysql_config_path="./mysql.cnf"):

        mysql_config = utils.load_config(mysql_config_path, ['database', 'host', 'port', 'user', 'password', 'ssl_ca'], 'client')

        self.host = mysql_config['host']
        self.user = mysql_config['user']
        self.port = int(mysql_config['port'])
        self.password = mysql_config['password']
        self.database = mysql_config['database']
        self.ssl = os.path.join(DATA_PATH, mysql_config['ssl_ca'])
        self.connection = None

    def connect(self):

        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                ssl=ssl.create_default_context(cafile=self.ssl)
            )
        except Exception as e:
            print(f"Error, can't connect to the database: {e}")
            return False
        return True

    def disconnect(self):

        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, query, params=None, retries=0):
        print("query -- ", query)
        print("param -- ", params)

        with self.connection.cursor() as cursor:
            try:
                cursor.execute(query, params)
                self.connection.commit()
                print("cursor -- ", cursor)
                return cursor
            except Exception as e:
                print(e)
                if retries < self.MAX_RETRIES:
                    self.disconnect()
                    self.connect()
                    print(f"Retrying query. Retry count: {retries + 1}")
                    time.sleep(self.RETRY_DELAY)
                    return self.execute_query(query, params, retries=retries + 1)
                else:
                    print("Max retries reached. Unable to execute query.")
                    return None

    def fetch_all(self, cursor):

        if cursor:
            return cursor.fetchall()
        return None

    def fetch_one(self, cursor):

        if cursor:
            return cursor.fetchone()
        return None

if __name__ == "__main__":
    db = MySQLDB(mysql_config_path="./mysql.cnf")  # Use config file

    if db.connect():
        cursor = db.execute_query("SELECT * FROM users")
        results = db.fetch_all(cursor)
        result = db.fetch_one(cursor)
        db.disconnect()



