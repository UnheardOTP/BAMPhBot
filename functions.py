import logging

# Error Logging
def init_logger(log_file="errors.log"):
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def log_Error(message):
    logging.error(message)

def get_beer_bitch_info(db):
    
    beer_bitch = db.query("select value from params where param = 'beer_bitch'")
    beer_bitch_beer = db.query("select value from params where param = 'beer_bitch_beer'")

    return (f"This years beer bitch is {beer_bitch[0]['value']} and the beer is {beer_bitch_beer[0]['value']}.")



