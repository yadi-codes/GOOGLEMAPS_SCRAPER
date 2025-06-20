# 🗺️ Google Maps Scraper

A Python-based scraper using Playwright that extracts place data (like name, address, phone, rating, reviews, location, and category) from Google Maps and stores it into a MySQL database.

---

## 🚀 Features

- 🔍 Scrape businesses from Google Maps based on category and location.
- 📍 Extracts:
  - Name
  - Address
  - Phone Number
  - Rating & Review Count
  - Latitude & Longitude
  - Category
- 🗃️ Stores scraped data in a normalized MySQL database.
- 🔁 Avoids duplicates by checking existing entries.
- 🧠 Modular and extensible structure.
- 🧪 Query interface to retrieve stored data by category, rating, name, etc.

---

## 🗂️ Project Structure

google-maps-scraper/
├── main.py # CLI runner for the scraper
├── config/
│ └── db_config.py # Database connection setup
├── models/
│ ├── db_handler.py # Database operations
│ └── business_models.py # Extraction logic
├── scraper/
│ └── maps_scraper.py # Google Maps scraping logic
├── utils/
│ └── helpers.py # Helper functions and utilities
├── data/
│ └── (optional CSVs or logs)
└── requirements.txt # Python dependencies

---

## 🧑‍💻 Technologies Used

- [Python 3.9+](https://www.python.org/)
- [Playwright](https://playwright.dev/python/)
- [MySQL](https://www.mysql.com/)
- [dotenv](https://pypi.org/project/python-dotenv/)
- [re (Regex)](https://docs.python.org/3/library/re.html)

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/google-maps-scraper.git
cd google-maps-scraper
2. Install Dependencies
bash
Copy
Edit
pip install -r requirements.txt
playwright install
3. Configure Environment Variables
Create a .env file in the root:

env
Copy
Edit
DB_HOST=localhost
DB_NAME=google_maps
DB_USER=root
DB_PASSWORD=yourpassword
4. Create MySQL Tables
Ensure you have the following tables:

sql
Copy
Edit
CREATE TABLE categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) UNIQUE
);

CREATE TABLE places (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255),
  address TEXT,
  phone VARCHAR(50),
  rating DECIMAL(2,1),
  review_count INT,
  scraped_at DATETIME,
  latitude DECIMAL(10, 7),
  longitude DECIMAL(10, 7)
);

CREATE TABLE place_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  place_id INT,
  category_id INT,
  FOREIGN KEY (place_id) REFERENCES places(id),
  FOREIGN KEY (category_id) REFERENCES categories(id)
);
📦 How to Use
Run the Scraper
bash
Copy
Edit
python main.py
Choose from the menu:

markdown
Copy
Edit
1. 🔍 Scrape new data
2. 📊 Query existing data
3. 🚪 Exit
Example Scrape
You’ll be prompted to enter:

Category: hotels, colleges, restaurants, etc.

Location: Chennai, Kochi, etc.

Number of results: e.g. 10

Querying Data
Query stored data by:

Category

Name

Minimum rating

Location

📌 Notes
Ensure stable internet and avoid scraping too fast to prevent CAPTCHA.

If some results are missing address or phone, the detail panel method can be triggered for accuracy.

Coordinates are parsed from Google Maps URLs.