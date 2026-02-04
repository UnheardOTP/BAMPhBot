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

def permanent_record(db, type, user, giver, reason):
  try:
    db.query("insert into permanent_record (user, point_type, reason, given_by) values (%s, %s, %s, %s)", (user, type, reason, giver))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))

#region Locker Inventory
def add_bottle(db, bottle_name, liquor_type):
  try:
    db.query("insert into locker_inventory (bottle_name, liquor_type) values ('%s', '%s')", (bottle_name, liquor_type,))

    db_conn.commit()

    return f"{bottle_name} added to locker inventory."
  except Exception as err:
    return err

def rem_bottle(bottle_id):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"delete from locker_inventory where id = {bottle_id}"
  try:
    db_cursor.execute(sql)
    
    value = db_cursor.fetchone()

    db_conn.commit()
    db_conn.close()

    result = value[0]

    return result
  except Exception as err:
    return err

def mark_bottle_low(bottle_id):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()
  
  sql = f"update locker_inventory set is_low = 1 where id = {bottle_id}"
  try:
    db_cursor.execute(sql)
    
    value = db_cursor.fetchone()

    db_conn.commit()
    db_conn.close()

    result = value[0]

    return result
  except Exception as err:
    return err

def get_locker_inventory():
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()
  
  sql = f"select * from locker_inventory"
  try:
    db_cursor.execute(sql)
    
    value = db_cursor.fetchall()

    db_conn.commit()
    db_conn.close()

    result = value

    return result
  except Exception as err:
    return err

#endregion





