## 10/23/25 

## First Running of web server 
- Start scripts via terminal = venv\Scripts\activate
- Flask runs on a web server on localhost:5000
- The terminal shows request logs (GET / HTTP/1.1 200)
- debug=True auto reloads when the file changes 
- Ctrl C stops the server 

## Apps
- Needs to be setup outside of the venv folder 

## 10/23/25

## Templates and Forms 
- Templates seperates HTML from the python logic 
- Makes for a cleaner and maintainable code 
- Flask automatticaly knows to look for the templates folder 

## Day 2: Routes and Multiple Pages 10/26/25

### Routes
- `@app.route('/path')` = Maps a URL to a function
- When user visits that URL, Flask runs that function
- The function returns what to display (usually a template)

### Multiple Pages
- Each page needs: a route in app.py + a template in templates/
- Example: `/about` route → about() function → about.html template

### The Request Flow
Browser → Flask → Route Match → Function → Template → Browser

### What I Built
- Created /about route
- Created about.html template  
- Tested both pages work independently
- Noticed CSS duplication (will fix later)

## Challenge 1 & 2 Completed!

### Added Quantity Field
- Added number input to form
- Captured it in Python with request.form.get()
- Added to dictionary and displayed it
- Learned: Template syntax {{ var1 }} text {{ var2 }}

### Sorted Items by Expiration Date
- Used sorted() function with lambda
- Key learning: WHERE to put the sort matters!
  - ❌ Outside functions = runs once at startup
  - ✅ Inside route function = runs every request
- Accessing dictionary values: item['key'] not item[index]

### Important Concept: Code Execution Timing
- Code at module level (outside functions) runs once when server starts
- Code inside route functions runs every time that route is called
- If you need current/fresh data, process it inside the route function

### Lambda Functions (new!)
- `lambda item: item['expiration']` = anonymous function
- Takes item, returns the expiration value
- Used for sorting/filtering

## Day 2 Complete - All Challenges Done! 🎉

### Challenge 3: Expiration Warnings
- Imported datetime module
- Calculated days until expiration for each item
- Added conditional styling in template
- Learned: {% if %} conditionals in Jinja2
- Learned: Date math with datetime objects

### Key Concepts Mastered
- When to calculate data (inside route functions for fresh data)
- How to modify dictionaries dynamically (adding 'days_left')
- Template conditional logic ({% if %}, {% elif %}, {% else %})
- String to date conversion (strptime)
- Date subtraction to get days difference

### Complete Feature List
✅ Add items with multiple fields
✅ Display items dynamically
✅ Sort by expiration date
✅ Visual warnings for expiring items
✅ Multiple routes/pages
✅ Form handling

### What I Built
A working fridge tracker that helps prevent food waste by:
- Tracking what's in my fridge
- Showing what expires soon
- Organizing by expiration date

### Next Steps (for future sessions)
- Add a database so data persists
- Add delete functionality
- Add edit functionality
- Deploy it somewhere so I can access it from my phone

## Database Integration Complete! 🗄️

### What I Added
- SQLite database for persistent storage
- Database helper functions (get_db_connection, init_db)
- SQL queries (CREATE TABLE, INSERT, SELECT)
- Proper connection management with try/finally

### Key Concepts Learned

**Database Basics:**
- Tables = spreadsheet-like structure with rows and columns
- Schema = blueprint defining column names and types
- Primary key = unique ID for each row (auto-incrementing)

**SQL Commands:**
- `CREATE TABLE` - creates the structure
- `INSERT INTO ... VALUES (?, ?, ?)` - adds data (? = placeholders for security)
- `SELECT * FROM ... ORDER BY` - retrieves data
- `conn.commit()` - saves changes permanently

**Connection Management:**
- Must open connection before querying
- Must close connection after querying
- try/finally ensures connection always closes (prevents database locks)
- timeout parameter gives more time for locked databases

**Why This Matters:**
- Data now persists across server restarts!
- Foundation for production applications
- Essential DevOps skill - all real apps need databases

### Bug Fixed
- "Database is locked" error
- Solution: try/finally blocks to ensure connections always close

### Project Structure Now
```
fridge-tracker/
├── venv/
├── templates/
│   ├── home.html
│   └── about.html
├── app.py
├── fridge.db          ← NEW! Our database file
└── LEARNING.md
```
## Delete Functionality Added - CRUD Complete!

### What I Added
- Delete button for each item
- Route with URL parameters: `/delete/<int:item_id>`
- SQL DELETE command with WHERE clause

### Key Concepts Learned

**URL Parameters:**
- `<int:item_id>` captures numbers from URLs
- Flask passes it as a function parameter
- Allows dynamic routes (different IDs)

**Forms for Actions:**
- Small forms with just a submit button
- method="POST" for actions that change data
- action="{{ url_for(...) }}" generates correct URLs

**SQL DELETE:**
- `DELETE FROM table WHERE condition`
- Always use WHERE or you delete everything!
- Placeholder (?) for safe value insertion

**CRUD Operations:**
- CREATE: /add route with INSERT
- READ: / route with SELECT
- UPDATE: (could add edit functionality)
- DELETE: /delete/<id> route with DELETE

### Current Feature List
✅ Add items (name, quantity, category, expiration, location)
✅ Display items sorted by expiration
✅ Calculate days until expiration
✅ Visual warnings for expiring items
✅ Delete items permanently
✅ Data persists across restarts
✅ Multiple pages

### What Makes This Production-Ready
- Database for persistence ✅
- Proper connection management ✅
- Form validation (HTML5 required) ✅
- User feedback (redirects) ✅
- Clean code organization ✅

### What's Still Missing for True Production
- User authentication (who owns which items?)
- Error handling (what if database fails?)
- Input validation (server-side)
- Security hardening
- Hosting/deployment
- Backup strategy
- Monitoring/logging

## CSS Layout Best Practices

### Flexbox vs Float
- ✅ USE: Flexbox for layouts (display: flex)
- ❌ AVOID: Float (causes overlapping, hard to predict)

### Common Flexbox Patterns
- Side by side: `display: flex; justify-content: space-between;`
- Centered: `display: flex; justify-content: center; align-items: center;`
- Buttons in row: `display: flex; gap: 5px;`

### Red Flags
- Multiple float: right → Use flexbox
- Using <br> for spacing → Use margin/padding
- Content overlapping → Usually float issue
- Long inline styles → Move to CSS classes

### The Container Pattern
Always wrap side-by-side content in a flex container:
```html
<div style="display: flex; justify-content: space-between;">
    <div>Left</div>
    <div>Right</div>
</div>
```

### Key Properties
- display: flex → Enable flexbox
- justify-content → Horizontal alignment (space-between, center, etc.)
- align-items → Vertical alignment (center, flex-start, etc.)
- gap → Spacing between flex items
- margin/padding → Spacing around elements (NOT <br>)


OperatorMeaningExample'le'Less than or equal (≤)days_left ≤ 3'lt'Less than (<)days_left < 3'ge'Greater than or equal (≥)days_left ≥ 7'gt'Greater than (>)days_left > 7'eq'Equal (==)days_left == 0'ne'Not equal (!=)days_left != 0

### Low Quantity Breakdown 
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: aliceblue; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h3 style="margin-right: 20px;">📊 Low Quantity Breakdown</h3>
        {% set low_items = items|selectattr('quantity', 'eq', 1)|list %}
            {% if low_items %}
                {% for item in low_items %}
                    <strong>{{item.name}} (only 1 left)</strong><br>
                {% endfor %}
            {% endif %}
    </div>

### Category Breakdown 
    <div style="
        /* The core Glassmorphism properties: transparency and blur */
        background: rgba(255, 255, 255, 0.15); /* Semi-transparent white */
        backdrop-filter: blur(10px); /* The frosted glass effect */
        -webkit-backdrop-filter: blur(10px); /* For Safari support */
        
        /* Standard modern card properties */
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 20px;
        
        /* Subtle border for definition and light shadow for depth */
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        
        /* Text color for contrast */
        color: #f0f0f0; /* Light text for dark backgrounds */
    ">
        <h3 style="margin-top: 0; margin-bottom: 25px; font-size: 1.75rem; font-weight: 700; color: #ffffff;">📊 Category Breakdown</h3>
        {% set fruit_count = items|selectattr('category', 'eq', 'Fruit')|list|length %}
        {% set vegetable_count = items|selectattr('category', 'eq', 'Vegetable')|list|length %}
        {% set dairy_count = items|selectattr('category', 'eq', 'Dairy')|list|length %}
        {% set meat_count = items|selectattr('category', 'eq', 'Meat')|list|length %}
        {% set other_count = items|selectattr('category', 'eq', 'Other')|list|length %}
        <ul style="list-style: none; padding: 0;">
            <li style="margin-bottom: 12px; font-size: 1.1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 5px;">**Fruit**: {{ fruit_count }} items</li>
            <li style="margin-bottom: 12px; font-size: 1.1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 5px;">**Vegetable**: {{ vegetable_count }} items</li>
            <li style="margin-bottom: 12px; font-size: 1.1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 5px;">**Dairy**: {{ dairy_count }} items</li>
            <li style="margin-bottom: 12px; font-size: 1.1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 5px;">**Meat**: {{ meat_count }} items</li>
            <li style="margin-bottom: 0; font-size: 1.1rem;">**Other**: {{ other_count }} items</li>
        </ul>
    </div>