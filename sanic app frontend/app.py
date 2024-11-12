from sanic import Sanic, response
from sanic.response import html, redirect
from sanic_session import Session
from jinja2 import Environment, FileSystemLoader, select_autoescape
from decimal import Decimal
import mysql.connector
import aiomysql


# Sanic App
app = Sanic(__name__)

#################### CONFIGURATION PART #################################


# Session configuration
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SECRET_KEY'] = 'mysecretkey'

# Initialize session middleware
Session(app)

template_path = "./templates"

# Serves files from the static folder to the URL /static
app.static('/static', './static')

env = Environment(
    loader=FileSystemLoader(template_path),
    autoescape=select_autoescape(['html', 'xml'])
)

# Define a custom function to generate URLs
def generate_url_for(route_name, **kwargs):
    # Check if the route_name is 'product' and 'id' parameter is provided
    if route_name == 'product' and 'id' in kwargs:
        # Convert the id parameter to int if it's provided
        kwargs['id'] = int(kwargs['id'])
    return app.url_for(route_name, **kwargs)

env.globals['url_for'] = generate_url_for

# Define the render_template function
def render_template(template_name, **context):
    template = env.get_template(template_name)
    return template.render(**context)

# MySQL Database Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "db": "flask_ecommerce_db",
}

############################################################################







########################## FUNCTION PART ###################################

# Function to retrieve user from database
async def get_user_from_db(email, password):
    async with aiomysql.create_pool(**db_config) as pool:
        async with pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM user WHERE email = %s AND password = %s", (email, password))
                user = await cursor.fetchone()
    return user

# Function to fetch product data from MySQL
def get_products():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM product")
    products = cursor.fetchall()
    cursor.close()
    connection.close()
    return products

# Function for finding product from MySQL
def find_product(id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM product WHERE id = %s", (id,))
    products = cursor.fetchall()
    cursor.close()
    connection.close()
    return products

# Function for count total item in cart
def count_total_item(user_id):
    # Execute SQL query to count occurrences of product_id in cart_item table for the given user_id
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    query = "SELECT COUNT(DISTINCT product_id) AS total FROM cart_item WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    total_items = result['total'] if result else 0
    cursor.close()
    connection.close()
    return total_items

# Function get Total Price
def get_total_price(product_total_prices):
    if product_total_prices:
        total_price = sum(Decimal(price) for price in product_total_prices)
        return total_price.quantize(Decimal('0.01'))  # Round to two decimal places
    else:
        return Decimal('0.00')  # Return 0 if the list is empty

# Function for get procuct detail
def get_product_details(product_id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM product WHERE id = %s", (product_id,))
    product_details = cursor.fetchone()
    cursor.close()
    connection.close()
    return product_details

# Function for get product on user inventory
def my_cart_get_product_inventory(user_id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cart_item WHERE user_id = %s", (user_id,))
    products = cursor.fetchall()
    cursor.close()
    connection.close()
    return products



##################### ROUTE ##########################


# Route for homepage and login
@app.route('/login', methods=['GET', 'POST'])
async def login(request):
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = await get_user_from_db(email, password)

        if user:
            # Successful login, store user info in session as dictionary
            request.ctx.session['user'] = {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name']
            }
            return redirect('/')
        else:
            # Invalid credentials, render login page with error message
            return html(render_template('login.html', error="Invalid credentials"))

    return html(render_template('login.html'))


# Route for logout
@app.route('/logout')
async def logout(request):
    if 'user' in request.ctx.session:
        del request.ctx.session['user']
    return redirect('/')

# Route for homepage
@app.route('/')
async def homepage(request):

    if 'user' in request.ctx.session:

        user_data = request.ctx.session['user']

        user_id = user_data['id']
        username = user_data['username']
        full_name = user_data['full_name']
        email = user_data['email']

        products = get_products()  # Fetch products
        total_item = count_total_item(user_id) # Count user product

        return html(render_template('index.html', title='Homepage', username=username, full_name=full_name, email=email, products=products, total_item=total_item))
    
    return html('Forbidden', status=403)


# Route for displaying a specific product
@app.route('/product/<id>')
async def product(request, id):
    if 'user' in request.ctx.session:

        user_data = request.ctx.session['user']

        user_id = user_data['id']
        username = user_data['username']
        full_name = user_data['full_name']
        email = user_data['email']

        products = find_product(id)
        total_item = count_total_item(user_id) # Count user products

        return html(render_template('product.html', username=username, full_name=full_name, email=email, products=products, total_item=total_item))
    
    return html(render_template('login.html'))


# My Cart Page
@app.route('/my-cart')
def my_cart(request):
    if 'user' in request.ctx.session:

        user_data = request.ctx.session['user']
        
        user_id = user_data['id']
        username = user_data['username']
        full_name = user_data['full_name']
        email = user_data['email']

        # get list product from cart_item database
        list_product = my_cart_get_product_inventory(user_id)

        products = []  # List to store product details
        product_total_prices = []  # List to store product total prices

        for item in list_product:

            # find product data from cart_item database
            product_id = item['product_id']
            product_quantity = item['quantity']
            
            # get product data from product database
            product_details = get_product_details(product_id)
            product_name = product_details['name']
            product_price = Decimal(product_details['price'])

            # get total price of the product
            product_total_price = product_quantity * product_price
            product_total_prices.append(product_total_price)  # Add product total price to the list

            # Append product details to the list
            products.append({
                'id': product_id,
                'quantity': product_quantity,
                'name': product_name,
                'price': product_total_price
            })

        # Calculate total price 
        total_price = get_total_price(product_total_prices) 
        
        return html(render_template('cart.html', products=products, total_price=total_price, username=username, full_name=full_name, email=email))
    
    return html(render_template('login.html'))


# Add to cart function
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart(request):
    if 'user' in request.ctx.session:

        user_data = request.ctx.session['user']
        user_id = user_data['id']
        data = request.json
        product_id = data.get('productId')

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            # Check if the product is already in the cart
            cursor.execute("SELECT * FROM cart_item WHERE user_id = %s AND product_id = %s", (user_id, product_id))
            existing_product = cursor.fetchone()

            if existing_product:
                # If the product is already in the cart, update its quantity
                new_quantity = existing_product[3] + 1
                cursor.execute("UPDATE cart_item SET quantity = %s WHERE user_id = %s AND product_id = %s", (new_quantity, user_id, product_id))
            else:
                # If the product is not in the cart, insert it with quantity 1
                cursor.execute("INSERT INTO cart_item (user_id, product_id, quantity) VALUES (%s, %s, 1)", (user_id, product_id))

            connection.commit()
            return response.json({'message': 'Product added to cart successfully'})
        
        except Exception as e:
            print("Error:", e)
            return response.json({'error': 'An error occurred while processing your request'}), 500
        finally:
            cursor.close()
            connection.close()

    else:
        return response.json({'error': 'User not logged in'})


# Delete Cart Item Function
@app.route('/delete-product', methods=['POST'])
async def delete_product(request):
    if 'user' in request.ctx.session:
        user_data = request.ctx.session['user']
        user_id = user_data['id']

        # Get the product ID from the request data
        data = request.json
        product_id = data.get('productId')


        try:
            # Connect to database
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM cart_item WHERE product_id = %s AND user_id = %s", (product_id, user_id))
            connection.commit()
            return response.json({'message': 'success' })

        finally:
            # Close the database connection
            cursor.close()
            connection.close()
    else:
        return response.json({'error': 'User not logged in'})
        
# Update Cart Page
@app.route('/update-cart', methods=['POST'])
def update_cart(request):
    if 'user' in request.ctx.session:

        user_data = request.ctx.session['user']
        user_id = user_data['id']

        data = request.json  # Get the JSON data sent from the client
        product_id = data.get('productId')
        quantity = data.get('quantity')
        
        def update_cart_item_quantity(user_id, product_id, new_quantity):
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            try:
                cursor.execute("""
                    UPDATE cart_item
                    SET quantity = %s
                    WHERE user_id = %s AND product_id = %s
                """, (new_quantity, user_id, product_id))
                connection.commit()
                return True
            except Exception as e:
                print("Error:", e)
                connection.rollback()
                return False
            finally:
                cursor.close()
                connection.close()
                
        success = update_cart_item_quantity(user_id, product_id, quantity)
        if success:
            return response.json({'success': True})
        else:
            return response.json({'success': False, 'message': 'Failed to update quantity'}), 500
    else:
        return response.json({'success': False, 'message': 'User not logged in'}), 401


# Payment Process
@app.route('/payment', methods=['GET', 'POST'])
def payment(request):
    if 'user' in request.ctx.session:

        user_data = request.ctx.session['user']
        
        user_id = user_data['id']

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("DELETE FROM cart_item WHERE user_id = %s", (user_id,))
        connection.commit()
        cursor.close()
        connection.close()

        return response.json({'success': True})
    
    else:
        return html(render_template('login.html'))

# Payment success redirected page
@app.route('/success')
def success(request):

    if 'user' in request.ctx.session:
        
        return html(render_template('success.html'))
        
    return html(render_template('login.html'))


# Running the Sanic app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
