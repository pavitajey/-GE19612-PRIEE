from pymongo import MongoClient

# Connect to MongoDB (Local)
client = MongoClient("mongodb://localhost:27017/")

# Create or connect to a database
db = client["tax_calculator"]

# Create or connect to a collection
users_collection = db["users"]

# Insert a sample document
user_data = {"username": "test_user", "email": "test@example.com"}
users_collection.insert_one(user_data)

print("User inserted successfully!")

# Fetch all users
all_users = users_collection.find()
for user in all_users:
    print(user)  # Print each document
