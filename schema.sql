CREATE TABLE users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT NOT NULL UNIQUE,
hash TEXT NOT NULL,
calorie_goal INTEGER DEFAULT 2000,
protein_goal REAL DEFAULT 150.0);
CREATE TABLE nutrition (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    food_name TEXT NOT NULL,
    calories INTEGER,
    protein REAL,
    carbs REAL,
    fats REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
