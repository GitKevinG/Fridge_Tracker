from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, date, timedelta
import sqlite3
import os 
from dotenv import load_dotenv
import requests
import json
import psycopg2 
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv('DATABASE_URL')


load_dotenv()

SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')

# Database helper functions
if DATABASE_URL:
    # Production: Use PostgreSQL
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    def get_db_connection():
        conn = psycopg2.connect(DATABASE_URL)
        return conn
else:
    # Development: Use SQLite
    def get_db_connection():
        conn = sqlite3.connect('fridge.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize the database with tables"""
    conn = get_db_connection()
    
    if DATABASE_URL:
        # PostgreSQL syntax
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fridge_items (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                category TEXT NOT NULL,
                expiration TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT DEFAULT 'fridge',
                price REAL,
                store TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY,
                item_name TEXT NOT NULL,
                store TEXT,
                price REAL NOT NULL,
                date_recorded TEXT NOT NULL,
                notes TEXT
            )
        ''')
        conn.commit()
        cursor.close()
    else:
        # SQLite syntax
        conn.execute('''
            CREATE TABLE IF NOT EXISTS fridge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                category TEXT NOT NULL,
                expiration TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT DEFAULT 'fridge',
                price REAL,
                store TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                store TEXT,
                price REAL NOT NULL,
                date_recorded TEXT NOT NULL,
                notes TEXT
            )
        ''')
        conn.commit()
    
    conn.close()

def migrate_db():
    """Add status column if it doesn't exist"""
    conn = get_db_connection()
    
    try:
        if DATABASE_URL:
            # PostgreSQL - use cursor
            cursor = conn.cursor()
            
            # Check if columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='fridge_items'
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'status' not in columns:
                cursor.execute("ALTER TABLE fridge_items ADD COLUMN status TEXT DEFAULT 'fridge'")
                conn.commit()
                print("Database migrated: added status column")
            
            if 'price' not in columns:
                cursor.execute("ALTER TABLE fridge_items ADD COLUMN price REAL")
                conn.commit()
                print("Database migrated: added price column")
            
            if 'store' not in columns:
                cursor.execute("ALTER TABLE fridge_items ADD COLUMN store TEXT")
                conn.commit()
                print("Database migrated: added store column")
            
            cursor.close()
            
        else:
            # SQLite - use conn.execute
            cursor = conn.execute("PRAGMA table_info(fridge_items)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'status' not in columns:
                conn.execute("ALTER TABLE fridge_items ADD COLUMN status TEXT DEFAULT 'fridge'")
                conn.commit()
                print("Database migrated: added status column")
            
            if 'price' not in columns:
                conn.execute("ALTER TABLE fridge_items ADD COLUMN price REAL")
                conn.commit()
                print("Database migrated: added price column")
            
            if 'store' not in columns:
                conn.execute("ALTER TABLE fridge_items ADD COLUMN store TEXT")
                conn.commit()
                print("Database migrated: added store column")
                
    finally:
        conn.close()

def init_price_history_table():
    """Create price_history table if it doesn't exist"""
    conn = get_db_connection()
    
    try:
        if DATABASE_URL:
            # PostgreSQL
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    store TEXT,
                    price REAL NOT NULL,
                    date_recorded TEXT NOT NULL,
                    notes TEXT
                )
            ''')
            conn.commit()
            cursor.close()
            print("Price history table initialized")
        else:
            # SQLite
            conn.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL,
                    store TEXT,
                    price REAL NOT NULL,
                    date_recorded TEXT NOT NULL,
                    notes TEXT
                )
            ''')
            conn.commit()
            print("Price history table initialized")
    finally:
        conn.close()


def search_recipes_by_ingredients(ingredients):
    """
    Search for recipes using Spoonacular API
    ingredients: list of ingredient names ['chicken', 'tomato', 'cheese']
    """
    if not SPOONACULAR_API_KEY:
        print("ERROR: No API key found!")
        return []
    
    # Spoonacular API endpoint
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    
    # Convert list to comma-separated string
    ingredients_str = ','.join(ingredients)
    
    # API parameters
    params = {
        'apiKey': SPOONACULAR_API_KEY,
        'ingredients': ingredients_str,
        'number': 12,  # Return 12 recipes
        'ranking': 2,  # Maximize used ingredients
        'ignorePantry': True  # Don't assume pantry staples
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise error for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return []

# Create the Flask app
app = Flask(__name__)
app.secret_key = 'secert-key'

# Initialize the database when the app starts
init_db()
migrate_db()
init_price_history_table()

@app.route('/')
def home():
    conn = get_db_connection()
    try:
        # Get all items from database
        items = conn.execute("SELECT * FROM fridge_items WHERE status = 'fridge' ORDER BY expiration").fetchall()
        
        # Calculate days left for each item
        today = date.today()
        items_with_days = []
        
        for item in items:
            item_dict = dict(item)
            expiration = datetime.strptime(item_dict['expiration'], '%Y-%m-%d').date()
            days_until_expiration = (expiration - today).days
            item_dict['days_left'] = days_until_expiration
            items_with_days.append(item_dict)
        
        return render_template('home.html', items=items_with_days)
    finally:
        conn.close()

@app.route('/recipes')
def recipes():
    conn = get_db_connection()
    try:
        # Get all items from fridge
        items = conn.execute(
            "SELECT * FROM fridge_items WHERE status = 'fridge'"
        ).fetchall()
        
        # Extract just the ingredient names
        ingredients = [item['name'] for item in items]
        
        # If no items, show message
        if not ingredients:
            return render_template('recipes.html', 
                                 recipes=[], 
                                 ingredients=[], 
                                 message="Your fridge is empty! Add some items first.")
        
        # Search for recipes
        recipes = search_recipes_by_ingredients(ingredients)
        
        return render_template('recipes.html', 
                             recipes=recipes, 
                             ingredients=ingredients,
                             message=None)
    finally:
        conn.close()

@app.route('/add-missing-ingredients', methods=['POST'])
def add_missing_ingredients():
    """Add missing recipe ingredients to shopping list"""
    ingredients = request.form.getlist('ingredients')
    
    conn = get_db_connection()
    try:
        added_count = 0
        for ingredient in ingredients:
            # Check if already in shopping list
            existing = conn.execute(
                "SELECT id FROM fridge_items WHERE name = ? AND status = 'shopping_list'",
                (ingredient,)
            ).fetchone()
            
            if not existing:
                # Add to shopping list
                conn.execute(
                    '''INSERT INTO fridge_items 
                       (name, quantity, category, expiration, location, status) 
                       VALUES (?, 1, 'Other', date('now', '+7 days'), 'Fridge', 'shopping_list')''',
                    (ingredient,)
                )
                added_count += 1
        
        conn.commit()
        
        if added_count > 0:
            flash(f'Added {added_count} ingredient(s) to your shopping list!', 'success')
        else:
            flash('All ingredients already in shopping list!', 'info')
        
    finally:
        conn.close()
    
    return redirect(url_for('recipes'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/shopping-list')
def shopping_list():
    conn = get_db_connection()
    try:
        # Get all items with status 'shopping_list'
        items = conn.execute(
            "SELECT * FROM fridge_items WHERE status = 'shopping_list' ORDER BY name"
        ).fetchall()
        
        # Convert to list of dicts
        items_list = [dict(item) for item in items]
        
        return render_template('shopping_list.html', items=items_list)
    finally:
        conn.close()

@app.route('/mark-purchased/<int:item_id>', methods=['POST'])
def mark_purchased(item_id):
    from datetime import timedelta
    
    conn = get_db_connection()
    try:
        # Calculate new expiration date (7 days from now)
        new_expiration = date.today() + timedelta(days=7)
        
        # Update item: move back to fridge with new expiration
        conn.execute(
            "UPDATE fridge_items SET status = 'fridge', expiration = ? WHERE id = ?",
            (new_expiration.strftime('%Y-%m-%d'), item_id)
        )
        conn.commit()
    finally:
        conn.close()
    
    return redirect(url_for('shopping_list'))


@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = get_db_connection()
    try:
        # Delete the item with this ID
        conn.execute('DELETE FROM fridge_items WHERE id = ?', (item_id,))
        conn.commit()
    finally:
        conn.close()

    referrer = request.referrer
    if referrer and 'shopping-list' in referrer:
        return redirect(url_for('shopping_list'))
    else:
        return redirect(url_for('home'))


@app.route('/move-to-shopping/<int:item_id>', methods=['POST'])
def move_to_shopping_list(item_id):
    conn = get_db_connection()
    try:
        # Update the item's status to 'shopping_list'
        conn.execute(
            "UPDATE fridge_items SET status = 'shopping_list' WHERE id = ?",
            (item_id,)
        )
        conn.commit()
    finally:
        conn.close()
    
    return redirect(url_for('home'))

@app.route('/price-history')
def price_history():
    """Show price history and trends"""
    conn = get_db_connection()
    try:
        # Get all price history, most recent first
        history = conn.execute(
            '''SELECT item_name, store, price, date_recorded 
               FROM price_history 
               ORDER BY date_recorded DESC'''
        ).fetchall()
        
        # Get unique items that have price history
        items_with_history = conn.execute(
            '''SELECT DISTINCT item_name, store 
               FROM price_history 
               ORDER BY item_name'''
        ).fetchall()
        
        # Calculate average prices per item per store
        averages = {}
        for item_store in items_with_history:
            item_name = item_store['item_name']
            store = item_store['store']
            
            # Get all prices for this item at this store
            prices = conn.execute(
                '''SELECT price, date_recorded 
                   FROM price_history 
                   WHERE item_name = ? AND store = ?
                   ORDER BY date_recorded DESC''',
                (item_name, store)
            ).fetchall()
            
            if prices:
                price_list = [p['price'] for p in prices]
                avg_price = sum(price_list) / len(price_list)
                min_price = min(price_list)
                max_price = max(price_list)
                latest_price = price_list[0]
                
                # Calculate trend (comparing latest to average)
                if latest_price > avg_price * 1.05:  # More than 5% above average
                    trend = 'up'
                elif latest_price < avg_price * 0.95:  # More than 5% below average
                    trend = 'down'
                else:
                    trend = 'stable'
                
                key = f"{item_name}|{store}"
                averages[key] = {
                    'item_name': item_name,
                    'store': store,
                    'average': avg_price,
                    'latest': latest_price,
                    'min': min_price,
                    'max': max_price,
                    'count': len(prices),
                    'trend': trend,
                    'prices': prices
                }
        
        return render_template('price_history.html', 
                             history=history, 
                             averages=averages)
    finally:
        conn.close()


@app.route('/add', methods=['POST'])
def add_item():
    # Get data from the form
    item_name = request.form.get('item_name')
    quantity = request.form.get('quantity')
    category = request.form.get('category')
    expiration_date = request.form.get('expiration_date')
    location = request.form.get('location')
    price = request.form.get('price')
    store = request.form.get('store')

    if price and price.strip():
        try:
            price = float(price)
        except ValueError:
            price = None
    else:
        price = None

    if not store or store.strip() == '':
        store = None
    
    conn = get_db_connection()
    try:
        # Insert the new item
        conn.execute(
            'INSERT INTO fridge_items (name, quantity, category, expiration, location, status, price, store) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (item_name, quantity, category, expiration_date, location, 'fridge', price, store)
        )

        if price is not None and item_name and store:
            conn.execute(
                '''INSERT INTO price_history (item_name, store, price, date_recorded)
                   VALUES (?, ?, ?, ?)''',
                (item_name, store, price, date.today().strftime('%Y-%m-%d'))
            )

        conn.commit()
    finally:
        conn.close()
    
    return redirect(url_for('home'))

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    """Edit an existing item"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Get updated data from form
        item_name = request.form.get('item_name')
        quantity = request.form.get('quantity')
        category = request.form.get('category')
        expiration_date = request.form.get('expiration_date')
        location = request.form.get('location')
        price = request.form.get('price')
        store = request.form.get('store')
        
        # Convert price to float if provided
        if price and price.strip():
            try:
                price = float(price)
            except ValueError:
                price = None
        else:
            price = None
        
        # If store is empty, set to None
        if not store or store.strip() == '':
            store = None
        
        try:
            # Get old item data to check if price changed
            old_item = conn.execute(
                'SELECT price, store, name FROM fridge_items WHERE id = ?',
                (item_id,)
            ).fetchone()
            
            # Update the item
            conn.execute(
                '''UPDATE fridge_items 
                   SET name = ?, quantity = ?, category = ?, expiration = ?, 
                       location = ?, price = ?, store = ?
                   WHERE id = ?''',
                (item_name, quantity, category, expiration_date, location, price, store, item_id)
            )
            
            # If price changed and exists, log new price in history
            if price is not None and store and item_name:
                if old_item['price'] != price:  # Price changed
                    conn.execute(
                        '''INSERT INTO price_history (item_name, store, price, date_recorded)
                           VALUES (?, ?, ?, ?)''',
                        (item_name, store, price, date.today().strftime('%Y-%m-%d'))
                    )
            
            conn.commit()
            flash(f'Updated {item_name}!', 'success')
            
            # Redirect back to where they came from
            referrer = request.referrer
            if referrer and 'shopping-list' in referrer:
                return redirect(url_for('shopping_list'))
            else:
                return redirect(url_for('home'))
        finally:
            conn.close()
    
    # GET request - show edit form
    try:
        item = conn.execute('SELECT * FROM fridge_items WHERE id = ?', (item_id,)).fetchone()
        if item is None:
            flash('Item not found!', 'error')
            return redirect(url_for('home'))
        return render_template('edit_item.html', item=item)
    finally:
        conn.close()

@app.route('/bulk-add', methods=['GET', 'POST'])
def bulk_add():
    """Add multiple items at once"""
    if request.method == 'POST':
        # Get the number of items being submitted
        item_count = int(request.form.get('item_count', 0))
        
        conn = get_db_connection()
        try:
            items_added = 0
            
            # Loop through each item in the form
            for i in range(item_count):
                # Get data for this item (fields are named like item_name_0, item_name_1, etc.)
                item_name = request.form.get(f'item_name_{i}', '').strip()
                
                # Skip empty rows
                if not item_name:
                    continue
                
                quantity = request.form.get(f'quantity_{i}', 1)
                category = request.form.get(f'category_{i}', 'Other')
                expiration_date = request.form.get(f'expiration_{i}')
                location = request.form.get(f'location_{i}', 'Fridge')
                store = request.form.get(f'store_{i}', '')
                price = request.form.get(f'price_{i}', '')
                
                # Convert price to float if provided
                if price and price.strip():
                    try:
                        price = float(price)
                    except ValueError:
                        price = None
                else:
                    price = None
                
                # If store is empty, set to None
                if not store or store.strip() == '':
                    store = None
                
                # Insert the item
                conn.execute(
                    '''INSERT INTO fridge_items 
                       (name, quantity, category, expiration, location, status, price, store) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (item_name, quantity, category, expiration_date, location, 'fridge', price, store)
                )
                
                # Log price history if price exists
                if price is not None and item_name and store:
                    conn.execute(
                        '''INSERT INTO price_history (item_name, store, price, date_recorded)
                           VALUES (?, ?, ?, ?)''',
                        (item_name, store, price, date.today().strftime('%Y-%m-%d'))
                    )
                
                items_added += 1
            
            conn.commit()
            flash(f'Successfully added {items_added} item(s)!', 'success')
            return redirect(url_for('home'))
            
        finally:
            conn.close()
    
    # GET request - show the form
    # Calculate default expiration (7 days from now)
    from datetime import datetime, timedelta
    default_expiration = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    return render_template('bulk_add.html', default_expiration=default_expiration)


if __name__ == '__main__':
    app.run(debug=True)