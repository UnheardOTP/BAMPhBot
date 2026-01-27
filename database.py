class database:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None

    def connect(self):
        if self.conn is None:
            import mysql.connector
            self.conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.conn.cursor(dictionary=True)
        return self.cursor

    def query(self, sql, params=None):
        self.connect()
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def commit(self):
        if self.conn:
            self.conn.commit()

    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
            self.conn = None
            self.cursor = None