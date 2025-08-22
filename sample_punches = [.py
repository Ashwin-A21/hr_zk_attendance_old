smple_punches = [
    # -------------------- Day 1 (2025-08-12) --------------------
    # Early Check-in (000)
    {"user_id": 000, "timestamp": datetime(2025, 8, 12, 8, 40), "status":4, "punch":0},
    {"user_id": 000, "timestamp": datetime(2025, 8, 12, 17, 30), "status":4, "punch":1},

    # Late Check-in (111)
    {"user_id": 111, "timestamp": datetime(2025, 8, 12, 9, 50), "status":4, "punch":0},
    {"user_id": 111, "timestamp": datetime(2025, 8, 12, 17, 30), "status":4, "punch":1},

    # Perfect Timing (222)
    {"user_id": 222, "timestamp": datetime(2025, 8, 12, 9, 0), "status":4, "punch":0},
    {"user_id": 222, "timestamp": datetime(2025, 8, 12, 17, 30), "status":4, "punch":1},

    # Half Day Early Exit (333)
    {"user_id": 333, "timestamp": datetime(2025, 8, 12, 9, 15), "status":4, "punch":0},
    {"user_id": 333, "timestamp": datetime(2025, 8, 12, 13, 0), "status":4, "punch":1},

    # Missed Punch-Out (444)
    {"user_id": 444, "timestamp": datetime(2025, 8, 12, 9, 10), "status":4, "punch":0},

    # Overtime (555)
    {"user_id": 555, "timestamp": datetime(2025, 8, 12, 8, 55), "status":4, "punch":0},
    {"user_id": 555, "timestamp": datetime(2025, 8, 12, 20, 30), "status":4, "punch":1},

    # Forgot Check-in (only punch-out) (666)
    {"user_id": 666, "timestamp": datetime(2025, 8, 12, 17, 30), "status":4, "punch":1},

    # Multiple Breaks (777)
    {"user_id": 777, "timestamp": datetime(2025, 8, 12, 9, 5), "status":4, "punch":0},
    {"user_id": 777, "timestamp": datetime(2025, 8, 12, 12, 20), "status":4, "punch":1},
    {"user_id": 777, "timestamp": datetime(2025, 8, 12, 13, 10), "status":4, "punch":0},
    {"user_id": 777, "timestamp": datetime(2025, 8, 12, 17, 40), "status":4, "punch":1},

    #   early check in late chec out Punch-In (888)
    {"user_id": 888, "timestamp": datetime(2025, 8, 12, 8, 55), "status":4, "punch":0},
    {"user_id": 888, "timestamp": datetime(2025, 8, 12, 18, 30), "status":4, "punch":1},

    # Full Day Normal (999)
    {"user_id": 999, "timestamp": datetime(2025, 8, 12, 9, 0), "status":4, "punch":0},
    {"user_id": 999, "timestamp": datetime(2025, 8, 12, 17, 30), "status":4, "punch":1},

    # Early checkin late check out (1111)
    {"user_id": 1111, "timestamp": datetime(2025, 8, 12, 8, 50), "status":4, "punch":0},
    {"user_id": 1111, "timestamp": datetime(2025, 8, 12, 17, 40), "status":4, "punch":1},

    # Early Early checkin Erly check out (2222)
    {"user_id": 2222, "timestamp": datetime(2025, 8, 12, 8, 50), "status":4, "punch":0},
    {"user_id": 2222, "timestamp": datetime(2025, 8, 12, 17, 15), "status":4, "punch":1},

    # Forgot Check out (4444)
    {"user_id": 4444, "timestamp": datetime(2025, 8, 12, 9, 0), "status":4, "punch":0},

    


    # -------------------- Day 2 (2025-08-13) --------------------
    # Early Check-in and early check out (000)
    {"user_id": 000, "timestamp": datetime(2025, 8, 13, 9, 0), "status":4, "punch":0},
    {"user_id": 000, "timestamp": datetime(2025, 8, 13, 17, 25), "status":4, "punch":1},

    # Late Check-in and late check out (111)
    {"user_id": 111, "timestamp": datetime(2025, 8, 13, 9, 0), "status":4, "punch":0},
    {"user_id": 111, "timestamp": datetime(2025, 8, 13, 17, 50), "status":4, "punch":1},

    # missed check in (222)
    {"user_id": 222, "timestamp": datetime(2025, 8, 13, 17, 50), "status":4, "punch":1},

    # Early Check in (333)
    {"user_id": 333, "timestamp": datetime(2025, 8, 13, 8, 40), "status":4, "punch":0},
    {"user_id": 333, "timestamp": datetime(2025, 8, 13, 17, 30), "status":4, "punch":1},

    # checkin and check out (444)
    {"user_id": 444, "timestamp": datetime(2025, 8, 13, 9, 0), "status":4, "punch":0},
    {"user_id": 444, "timestamp": datetime(2025, 8, 13, 17, 30), "status":4, "punch":1},

    # late checkin early check out (555)
    {"user_id": 555, "timestamp": datetime(2025, 8, 13, 9, 15), "status":4, "punch":0},
    {"user_id": 555, "timestamp": datetime(2025, 8, 13, 16, 30), "status":4, "punch":1},

    # Forgot Check-out (666)
    {"user_id": 666, "timestamp": datetime(2025, 8, 13, 8, 56), "status":4, "punch":0},

    # checkin late check out (777)
    {"user_id": 777, "timestamp": datetime(2025, 8, 13, 9, 0), "status":4, "punch":0},
    {"user_id": 777, "timestamp": datetime(2025, 8, 13, 18, 0), "status":4, "punch":1},

    # late checkin and late check out (888)

    {"user_id": 888, "timestamp": datetime(2025, 8, 13, 9, 30), "status":4, "punch":0},
    {"user_id": 888, "timestamp": datetime(2025, 8, 13, 18, 0), "status":4, "punch":1},

    # late checkin and late early check out  (999)
    {"user_id": 999, "timestamp": datetime(2025, 8, 13, 10, 0), "status":4, "punch":0},
    {"user_id": 999, "timestamp": datetime(2025, 8, 13, 17, 0), "status":4, "punch":1},

    # early checkin and check out  (1111)
    {"user_id": 1111, "timestamp": datetime(2025, 8, 13, 8, 30), "status":4, "punch":0},
    {"user_id": 1111, "timestamp": datetime(2025, 8, 13, 17, 30), "status":4, "punch":1},

    # late checkin and late check out  (2222)
    {"user_id": 2222, "timestamp": datetime(2025, 8, 13, 9, 15), "status":4, "punch":0},
    {"user_id": 2222, "timestamp": datetime(2025, 8, 13, 18, 0), "status":4, "punch":1},

    # Early Early checkin late check out (3333)
    {"user_id": 3333, "timestamp": datetime(2025, 8, 13, 8, 55), "status":4, "punch":0},
    {"user_id": 3333, "timestamp": datetime(2025, 8, 13, 17, 35), "status":4, "punch":1},

    #absent 444


    # -------------------- Day 3 (2025-08-14) --------------------
    # (Similar variations repeated with slight time differences for realism)

    # late checkin and late check out
    {"user_id": 000, "timestamp": datetime(2025, 8, 14, 9, 25), "status":4, "punch":0},
    {"user_id": 000, "timestamp": datetime(2025, 8, 14, 17, 35), "status":4, "punch":1},

    # Early checkin and early check out
    {"user_id": 111, "timestamp": datetime(2025, 8, 14, 8, 45), "status":4, "punch":0},
    {"user_id": 111, "timestamp": datetime(2025, 8, 14, 16, 35), "status":4, "punch":1},

    # Early checkin and check out
    {"user_id": 222, "timestamp": datetime(2025, 8, 14, 8, 45), "status":4, "punch":0},
    {"user_id": 222, "timestamp": datetime(2025, 8, 14, 17, 30), "status":4, "punch":1},

    # Checkin and forgot to check out
    {"user_id": 333, "timestamp": datetime(2025, 8, 14, 9, 0), "status":4, "punch":0},

    # Early checkin and check out
    {"user_id": 444, "timestamp": datetime(2025, 8, 14, 8, 50), "status":4, "punch":0},
    {"user_id": 444, "timestamp": datetime(2025, 8, 14, 17, 30), "status":4, "punch":1},
   
    #forgot to checkin
    {"user_id": 555, "timestamp": datetime(2025, 8, 14, 17, 45), "status":4, "punch":1},

    # normal days
    {"user_id": 666, "timestamp": datetime(2025, 8, 14, 9, 0), "status":4, "punch":0},
    {"user_id": 666, "timestamp": datetime(2025, 8, 14, 17, 30), "status":4, "punch":1},

    #forgot to check in
    {"user_id": 777, "timestamp": datetime(2025, 8, 14, 16, 30), "status":4, "punch":1},

    #NORMAL DAYS
    {"user_id": 888, "timestamp": datetime(2025, 8, 14, 9, 0), "status":4, "punch":0},
    {"user_id": 888, "timestamp": datetime(2025, 8, 14, 17, 30), "status":4, "punch":1},

    #Early checkin and late check out
    {"user_id": 999, "timestamp": datetime(2025, 8, 14, 8, 45), "status":4, "punch":0},
    {"user_id": 999, "timestamp": datetime(2025, 8, 14, 18, 0), "status":4, "punch":1},

    #late checkin and late check out
    {"user_id": 1111, "timestamp": datetime(2025, 8, 14, 9, 45), "status":4, "punch":0},
    {"user_id": 1111, "timestamp": datetime(2025, 8, 14, 17, 45), "status":4, "punch":1},

    #Checkin and Checkout
    {"user_id": 2222, "timestamp": datetime(2025, 8, 14, 9, 0), "status":4, "punch":0},
    {"user_id": 2222, "timestamp": datetime(2025, 8, 14, 17, 30), "status":4, "punch":1},

    # Late checkin and early checkout
    {"user_id": 3333, "timestamp": datetime(2025, 8, 14, 9, 40), "status":4, "punch":0},
    {"user_id": 3333, "timestamp": datetime(2025, 8, 14, 15, 30), "status":4, "punch":1},
     
     # forgot check in
    {"user_id": 4444, "timestamp": datetime(2025, 8, 14, 17, 30), "status":4, "punch":0},

]
