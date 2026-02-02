from database import database

def error_log(err):
  db = database(db_host, db_user, db_password, db_database)  
  
  db.query("insert into bot_error_log (datetime, error_message) values (%s, %s)", (datetime.now(), err))

def get_beer_bitch_info(db):
    
    beer_bitch = db.query("select value from params where param = 'beer_bitch'")
    beer_bitch_beer = db.query("select value from params where param = 'beer_bitch_beer'")

    return (f"This years beer bitch is {beer_bitch[0]['value']} and the beer is {beer_bitch_beer[0]['value']}.")

def last_course_status(db):
    last_course_status = db.query("select value from params where param = 'last_course_status'")

    return last_course_status[0]['value']

def set_course_status(db, course_status):
    db.query("UPDATE params SET value = %s WHERE param = 'last_course_status'", (course_status,))
    db.commit()

    return 0;




