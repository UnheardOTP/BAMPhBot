import logging
import json
from database import database

#region Secrets
with open('secrets.txt', 'r') as f:
    data = f.read()
    f.close()

secrets = json.loads(data)

db_host=secrets['HOST']
db_user=secrets['USER']
db_password=secrets['PASSWORD']
db_database=secrets['DATABASE']
#endregion Secrets

# Error Logging
def init_logger(log_file="errors.log"):
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def log_Error(message):
    logging.error(message)


def get_beer_bitch_info():
    db = database(db_host, db_user, db_password, db_database)
    beer_bitch = db.query("select value from params where param = 'beer_bitch'")
    beer_bitch_beer = db.query("select value from params where param = 'beer_bitch_beer'")

    return (f'This years beer bitch is {beer_bitch} and the beer is {beer_bitch_beer}.')



