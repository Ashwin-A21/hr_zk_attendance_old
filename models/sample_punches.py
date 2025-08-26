from datetime import datetime

data = [
 
    # early 
    {"user_id": 111, "timestamp": datetime(2025, 8, 10, 9, 0), "status": 4, "punch": 0},
    {"user_id": 111, "timestamp": datetime(2025, 8, 11, 15, 0), "status": 4, "punch": 0},
    # {"user_id": 111, "timestamp": datetime(2025, 8, 10, 18, 0), "status": 4, "punch": 0},
    #normal

    {"user_id": 222, "timestamp": datetime(2025, 8, 12, 8, 58, 0), "status": 4, "punch": 0},
    {"user_id": 222, "timestamp": datetime(2025, 8, 12, 12, 1, 0), "status": 4, "punch": 0},
    {"user_id": 222, "timestamp": datetime(2025, 8, 12, 12, 59, 0), "status": 4, "punch": 0},
    {"user_id": 222, "timestamp": datetime(2025, 8, 12, 17, 2, 0), "status": 4, "punch": 0},

    # Early Start, Late Finish with Lunch Break (Employee 333)
    # Check-in, Break-out, Break-in, Check-out
    {"user_id": 333, "timestamp": datetime(2025, 8, 12, 7, 15, 0), "status": 4, "punch": 0},
    {"user_id": 333, "timestamp": datetime(2025, 8, 12, 12, 30, 0), "status": 4, "punch": 0},
    {"user_id": 333, "timestamp": datetime(2025, 8, 12, 13, 28, 0), "status": 4, "punch": 0},
    {"user_id": 333, "timestamp": datetime(2025, 8, 12, 18, 45, 0), "status": 4, "punch": 0},

     {"user_id": 444, "timestamp": datetime(2025, 8, 13, 8, 45, 0), "status": 4, "punch": 0},

    {"user_id": 555, "timestamp": datetime(2025, 8, 13, 17, 40, 0), "status": 4, "punch": 0},

     {"user_id": 222, "timestamp": datetime(2025, 8, 26, 9, 45), "status": 4, "punch": 0},

    # {"user_id": 111, "timestamp": datetime(2025, 8, 11, 8, 30), "status": 4, "punch": 0},
    # {"user_id": 111, "timestamp": datetime(2025, 8, 11, 18, 0), "status": 4, "punch": 0},
    # #missing checkin
    # {"user_id": 111, "timestamp": datetime(2025, 8, 12, 18, 0), "status": 4, "punch": 0},
    #late bathe 
#     {"user_id": 111, "timestamp": datetime(2025, 8, 13, 9, 30), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 13, 18, 0), "status": 4, "punch": 0},
#     #mix
#     {"user_id": 111, "timestamp": datetime(2025, 8, 14, 8, 30), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 14, 11, 0), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 14, 3, 30), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 14, 18, 0), "status": 4, "punch": 0},

#     #late bathe bega poye
#     {"user_id": 111, "timestamp": datetime(2025, 8, 15, 10, 0), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 15, 16, 0), "status": 4, "punch": 0},
#     #begaapoye 
#     {"user_id": 111, "timestamp": datetime(2025, 8, 16, 8, 30), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 16, 16, 0), "status": 4, "punch": 0},





#     #missing checkout
#     {"user_id": 111, "timestamp": datetime(2025, 8, 17, 9, 30), "status": 4, "punch": 0},
    
#     # norml
#     {"user_id": 111, "timestamp": datetime(2025, 8, 18, 8, 30), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 18, 18, 0), "status": 4, "punch": 0},
   
#     {"user_id": 111, "timestamp": datetime(2025, 8, 11, 8, 30), "status": 4, "punch": 0},
#     {"user_id": 111, "timestamp": datetime(2025, 8, 11, 18, 0), "status": 4, "punch": 0},
# #
#     {"user_id": 111, "timestamp": datetime(2025, 8, 12, 18, 30), "status": 4, "punch": 0},

#     {"user_id": 111, "timestamp": datetime(2025, 8, 13, 8, 0), "status": 4, "punch": 0},
    
#     {"user_id": 111, "timestamp": datetime(2025, 8, 14, 18, 30), "status": 4, "punch": 0},


#     {"user_id": 111, "timestamp": datetime(2025, 8, 21, 18, 30), "status": 4, "punch": 0},

    #  {"user_id": 999, "timestamp": datetime(2025, 8, 21, 18, 15), "status": 4, "punch": 0},

    # {"user_id": 222, "timestamp": datetime(2025, 8, 20, 8, 30), "status": 4, "punch": 0},
    # {"user_id": 222, "timestamp": datetime(2025, 8, 20, 16, 30), "status": 4, "punch": 0},

    # {"user_id": 222, "timestamp": datetime(2025, 8, 22, 8, 30), "status": 4, "punch": 0},

    #  {"user_id": 333, "timestamp": datetime(2025, 8, 20, 9, 30), "status": 4, "punch": 0},
]