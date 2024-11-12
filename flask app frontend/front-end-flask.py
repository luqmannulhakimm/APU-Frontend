from flask import Flask, render_template, request, url_for, session, redirect, jsonify, abort
from decimal import Decimal
import mysql.connector
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = "93dcbe81bb3a1211f71818849ba2bd08"

#__________Mysql Database_________#

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "flask_ecommerce_db"
}

#________________________________#

###################################### Function Section ########################################

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

################################# ROUTE SECTION ###########################################

# Route for homepage, also make product display function
@app.route('/')
def homepage():

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }

    if 'user' in session:
        user_id = session['user']['id']
        username = session['user']['username']
        full_name = session['user']['full_name']
        email = session['user']['email']

        products = get_products()  # Fetch products
        total_item = count_total_item(user_id) # Count user product

        return render_template('index.html', title='Homepage',
                                username=username, full_name=full_name, email=email, products=products, total_item=total_item)
    
    return abort(403)


# Function for display specific product on product page
@app.route('/product/<int:id>')
def product(id):

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }

    if 'user' in session:
        user_id = session['user']['id']
        username = session['user']['username']
        full_name = session['user']['full_name']
        email = session['user']['email']

        products = find_product(id)
        total_item = count_total_item(user_id) # Count user product

        return render_template('product.html', username=username, full_name=full_name, email=email, products=products, total_item=total_item)
    
    return abort(403)

# Add to cart function
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }

    if 'user' in session:
        user_id = session['user']['id']
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
            return jsonify({'message': 'Product added to cart successfully'})
        
        except Exception as e:
            print("Error:", e)
            return jsonify({'error': 'An error occurred while processing your request'}), 500
        finally:
            cursor.close()
            connection.close()

    else:
        return jsonify({'error': 'User not logged in'})

# Delete Cart Item Function
@app.route('/delete-product', methods=['POST'])
def delete_product():

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }

    if 'user' in session:
        user_id = session['user']['id']

        # Get the product ID from the request data
        data = request.get_json()
        product_id = data.get('productId')

        # Check if the product ID is provided
        if not product_id:
            return jsonify({'error': 'Product ID is required'}), 400

        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        try:
            # Execute the SQL query to delete the product from cart_item table
            cursor.execute("DELETE FROM cart_item WHERE product_id = %s AND user_id = %s", (product_id, user_id))
            connection.commit()
            return jsonify({'message': f'Product with ID {product_id} deleted successfully'}), 200
        except mysql.connector.Error as err:
            # Handle any database errors
            print("Error:", err)
            return jsonify({'error': 'An error occurred while deleting the product'}), 500
        finally:
            # Close the database connection
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'User not logged in'})

# My Cart Page
@app.route('/my-cart')
def my_cart():

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }

    if 'user' in session:
        user_id = session['user']['id']
        username = session['user']['username']
        full_name = session['user']['full_name']
        email = session['user']['email']

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
        
        return render_template('cart.html', products=products, total_price=total_price, username=username, full_name=full_name, email=email)
    
    return redirect(url_for('login'))


@app.route('/update-cart', methods=['POST'])
def update_cart():

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }

    if 'user' in session:
        user_id = session['user']['id']
        data = request.json  # Get the JSON data sent from the client
        product_id = data['productId']
        quantity = data['quantity']
        
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
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'message': 'Failed to update quantity'}), 500
    else:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

# Payment Process
@app.route('/payment', methods=['GET', 'POST'])
def payment():

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }
    

    if 'user' in session:
        user_id = session['user']['id']

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("DELETE FROM cart_item WHERE user_id = %s", (user_id,))
        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True}), 200
    
    else:
        return redirect(url_for('login'))

# Payment success redirected page
@app.route('/success')
def success():

    session['user'] = {
    'id': '1',    
    'username': 'Luqmannul',        
    'email': 'luqmannulhakimsul42@gmail.com',      
    'full_name': 'Luqmannul Hakim',
    }

    if 'user' in session:
        return render_template('success.html')
        
    return redirect(url_for('login'))


# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():

        session['user'] = {
            'id': '1',    
            'username': 'Luqmannul',        
            'email': 'luqmannulhakimsul42@gmail.com',      
            'full_name': 'Luqmannul Hakim',
        }

        return redirect(url_for('homepage'))   

# Clear Session / Log Out
@app.route('/logout')
def logout():
    session.clear()
    return "Successfully Logout"

# Run flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
