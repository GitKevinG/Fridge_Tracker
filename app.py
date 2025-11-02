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




# Create the Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Get API key from environment variable (production) or hardcode (development)
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY', 'your-api-key-here')

# Check if we're on Render (production) or local (development)
DATABASE_URL = os.getenv('DATABASE_URL')

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

# Helper functions for database operations
def execute_query(conn, query, params=None):
    """Execute a SELECT query and return results"""
    if DATABASE_URL:
        # PostgreSQL
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Fetch results and convert to dict
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        cursor.close()
        return results
    else:
        # SQLite
        if params:
            return conn.execute(query, params).fetchall()
        else:
            return conn.execute(query).fetchall()

def execute_insert(conn, query, params):
    """Execute an INSERT/UPDATE/DELETE query"""
    if DATABASE_URL:
        # PostgreSQL
        cursor = conn.cursor()
        cursor.execute(query, params)
        cursor.close()
    else:
        # SQLite
        conn.execute(query, params)

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
    """Add status, price, and store columns if they don't exist"""
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

# Initialize the database when the app starts
init_db()
migrate_db()
init_price_history_table()

# Helper function to calculate days until expiration
def calculate_days_left(expiration_date_str):
    """Calculate days left until expiration"""
    try:
        expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d').date()
        today = date.today()
        days_left = (expiration_date - today).days
        return days_left
    except:
        return 999  # Default if date parsing fails

@app.route('/')
def home():
    """Display all fridge items"""
    conn = get_db_connection()
    try:
        items = execute_query(conn, "SELECT * FROM fridge_items WHERE status = 'fridge' ORDER BY expiration")
        
        # Add days_left calculation to each item
        items_with_days = []
        for item in items:
            item_dict = dict(item)
            item_dict['days_left'] = calculate_days_left(item_dict['expiration'])
            items_with_days.append(item_dict)
        
        return render_template('home.html', items=items_with_days)
    finally:
        conn.close()

@app.route('/add', methods=['POST'])
def add_item():
    """Add a new item to the fridge"""
    item_name = request.form.get('item_name')
    quantity = request.form.get('quantity')
    category = request.form.get('category')
    expiration_date = request.form.get('expiration_date')
    location = request.form.get('location')
    
    # Get price and store
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
    
    conn = get_db_connection()
    try:
        execute_insert(conn, 
            '''INSERT INTO fridge_items 
               (name, quantity, category, expiration, location, status, price, store) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''' if DATABASE_URL else
            '''INSERT INTO fridge_items 
               (name, quantity, category, expiration, location, status, price, store) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (item_name, quantity, category, expiration_date, location, 'fridge', price, store)
        )
        
        # If item has a price, log it in price history
        if price is not None and item_name and store:
            execute_insert(conn,
                '''INSERT INTO price_history (item_name, store, price, date_recorded)
                   VALUES (%s, %s, %s, %s)''' if DATABASE_URL else
                '''INSERT INTO price_history (item_name, store, price, date_recorded)
                   VALUES (?, ?, ?, ?)''',
                (item_name, store, price, date.today().strftime('%Y-%m-%d'))
            )
        
        conn.commit()
    finally:
        conn.close()
    
    return redirect(url_for('home'))

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    """Delete an item from the fridge"""
    conn = get_db_connection()
    try:
        execute_insert(conn, 
            'DELETE FROM fridge_items WHERE id = %s' if DATABASE_URL else 'DELETE FROM fridge_items WHERE id = ?',
            (item_id,)
        )
        conn.commit()
    finally:
        conn.close()
    
    # Redirect back to where they came from
    referrer = request.referrer
    if referrer and 'shopping-list' in referrer:
        return redirect(url_for('shopping_list'))
    else:
        return redirect(url_for('home'))

@app.route('/move-to-shopping/<int:item_id>', methods=['POST'])
def move_to_shopping_list(item_id):
    """Move an item to the shopping list"""
    conn = get_db_connection()
    try:
        execute_insert(conn,
            "UPDATE fridge_items SET status = %s WHERE id = %s" if DATABASE_URL else
            "UPDATE fridge_items SET status = ? WHERE id = ?",
            ('shopping_list', item_id)
        )
        conn.commit()
        flash('Item moved to shopping list!', 'success')
    finally:
        conn.close()
    
    return redirect(url_for('home'))

@app.route('/shopping-list')
def shopping_list():
    """Display shopping list"""
    conn = get_db_connection()
    try:
        items = execute_query(conn, "SELECT * FROM fridge_items WHERE status = 'shopping_list'")
        return render_template('shopping_list.html', items=items)
    finally:
        conn.close()

@app.route('/mark-purchased/<int:item_id>', methods=['POST'])
def mark_purchased(item_id):
    """Mark an item as purchased and remove from shopping list"""
    conn = get_db_connection()
    try:
        execute_insert(conn,
            'DELETE FROM fridge_items WHERE id = %s' if DATABASE_URL else 'DELETE FROM fridge_items WHERE id = ?',
            (item_id,)
        )
        conn.commit()
        flash('Item marked as purchased!', 'success')
    finally:
        conn.close()
    
    return redirect(url_for('shopping_list'))

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    """Edit an existing item"""
    conn = get_db_connection()
    
    if request.method == 'POST':
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
            old_item = execute_query(conn,
                'SELECT price, store, name FROM fridge_items WHERE id = %s' if DATABASE_URL else
                'SELECT price, store, name FROM fridge_items WHERE id = ?',
                (item_id,)
            )
            
            if old_item:
                old_item = old_item[0]
            
            # Update the item
            execute_insert(conn,
                '''UPDATE fridge_items 
                   SET name = %s, quantity = %s, category = %s, expiration = %s, 
                       location = %s, price = %s, store = %s
                   WHERE id = %s''' if DATABASE_URL else
                '''UPDATE fridge_items 
                   SET name = ?, quantity = ?, category = ?, expiration = ?, 
                       location = ?, price = ?, store = ?
                   WHERE id = ?''',
                (item_name, quantity, category, expiration_date, location, price, store, item_id)
            )
            
            # If price changed and exists, log new price in history
            if price is not None and store and item_name and old_item:
                if old_item['price'] != price:
                    execute_insert(conn,
                        '''INSERT INTO price_history (item_name, store, price, date_recorded)
                           VALUES (%s, %s, %s, %s)''' if DATABASE_URL else
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
        item = execute_query(conn, 
            'SELECT * FROM fridge_items WHERE id = %s' if DATABASE_URL else 'SELECT * FROM fridge_items WHERE id = ?',
            (item_id,)
        )
        if not item:
            flash('Item not found!', 'error')
            return redirect(url_for('home'))
        return render_template('edit_item.html', item=item[0])
    finally:
        conn.close()

@app.route('/bulk-add', methods=['GET', 'POST'])
def bulk_add():
    """Add multiple items at once"""
    if request.method == 'POST':
        item_count = int(request.form.get('item_count', 0))
        
        conn = get_db_connection()
        try:
            items_added = 0
            
            for i in range(item_count):
                item_name = request.form.get(f'item_name_{i}', '').strip()
                
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
                execute_insert(conn,
                    '''INSERT INTO fridge_items 
                       (name, quantity, category, expiration, location, status, price, store) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''' if DATABASE_URL else
                    '''INSERT INTO fridge_items 
                       (name, quantity, category, expiration, location, status, price, store) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (item_name, quantity, category, expiration_date, location, 'fridge', price, store)
                )
                
                # Log price history if price exists
                if price is not None and item_name and store:
                    execute_insert(conn,
                        '''INSERT INTO price_history (item_name, store, price, date_recorded)
                           VALUES (%s, %s, %s, %s)''' if DATABASE_URL else
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
    default_expiration = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    return render_template('bulk_add.html', default_expiration=default_expiration)

@app.route('/price-history')
def price_history():
    """Show price history and trends"""
    conn = get_db_connection()
    try:
        # Get all price history, most recent first
        history = execute_query(conn,
            '''SELECT item_name, store, price, date_recorded 
               FROM price_history 
               ORDER BY date_recorded DESC'''
        )
        
        # Get unique items that have price history
        items_with_history = execute_query(conn,
            '''SELECT DISTINCT item_name, store 
               FROM price_history 
               ORDER BY item_name'''
        )
        
        # Calculate average prices per item per store
        averages = {}
        for item_store in items_with_history:
            item_name = item_store['item_name']
            store = item_store['store']
            
            # Get all prices for this item at this store
            prices = execute_query(conn,
                '''SELECT price, date_recorded 
                   FROM price_history 
                   WHERE item_name = %s AND store = %s
                   ORDER BY date_recorded DESC''' if DATABASE_URL else
                '''SELECT price, date_recorded 
                   FROM price_history 
                   WHERE item_name = ? AND store = ?
                   ORDER BY date_recorded DESC''',
                (item_name, store)
            )
            
            if prices:
                price_list = [p['price'] for p in prices]
                avg_price = sum(price_list) / len(price_list)
                min_price = min(price_list)
                max_price = max(price_list)
                latest_price = price_list[0]
                
                # Calculate trend
                if latest_price > avg_price * 1.05:
                    trend = 'up'
                elif latest_price < avg_price * 0.95:
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

# Recipe helper function
def get_recipes(ingredients, number=12):
    """Get recipe suggestions from Spoonacular API"""
    if not ingredients:
        return []
    
    url = 'https://api.spoonacular.com/recipes/findByIngredients'
    params = {
        'ingredients': ','.join(ingredients),
        'number': number,
        'ranking': 2,
        'ignorePantry': True,
        'apiKey': SPOONACULAR_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except:
        return []

@app.route('/recipes')
def recipes():
    """Show recipe suggestions based on fridge items"""
    conn = get_db_connection()
    try:
        items = execute_query(conn, "SELECT * FROM fridge_items WHERE status = 'fridge'")
        
        # Get ingredient names
        ingredients = [item['name'] for item in items]
        
        # Get recipe suggestions
        recipes_data = get_recipes(ingredients, number=12)
        
        return render_template('recipes.html', 
                             recipes=recipes_data, 
                             ingredients=ingredients)
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
            existing = execute_query(conn,
                "SELECT id FROM fridge_items WHERE name = %s AND status = 'shopping_list'" if DATABASE_URL else
                "SELECT id FROM fridge_items WHERE name = ? AND status = 'shopping_list'",
                (ingredient,)
            )
            
            if not existing:
                # Add to shopping list
                execute_insert(conn,
                    '''INSERT INTO fridge_items 
                       (name, quantity, category, expiration, location, status) 
                       VALUES (%s, 1, 'Other', %s, 'Fridge', 'shopping_list')''' if DATABASE_URL else
                    '''INSERT INTO fridge_items 
                       (name, quantity, category, expiration, location, status) 
                       VALUES (?, 1, 'Other', date('now', '+7 days'), 'Fridge', 'shopping_list')''',
                    (ingredient, (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')) if DATABASE_URL else (ingredient,)
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
    """About page"""
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)