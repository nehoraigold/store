from bottle import run, template, static_file, get, post, delete, request, response
import json
import pymysql

connection = pymysql.connect(host='localhost',
                             user='root',
                             password='root',
                             db='store',
                             charset='utf8',
                             cursorclass=pymysql.cursors.DictCursor)


def json_resp(status, msg, code, field=None, field_contents=None):
    new_dict = {
        "STATUS": status,
        "MSG": msg,
        "CODE": code,
    }
    if field:
        new_dict[field] = field_contents
    if msg:
        response["status_line"] = msg
    return json.dumps(new_dict)


def intErr():
    return json_resp("ERROR", "Internal error", 500)


@get("/admin")
def admin_portal():
    return template("pages/admin.html")


@get("/")
def index():
    return template("index.html")


@get('/js/<filename:re:.*\.js>')
def javascripts(filename):
    return static_file(filename, root='js')


@get('/css/<filename:re:.*\.css>')
def stylesheets(filename):
    return static_file(filename, root='css')


@get('/images/<filename:re:.*\.(jpg|png|gif|ico)>')
def images(filename):
    return static_file(filename, root='images')


@post('/category')
def add_category():
    new_cat = request.forms.get('name')
    if not new_cat:
        return json_resp("ERROR", "Name parameter is missing", 400)
    try:
        with connection.cursor() as cursor:
            look_for_existing_cat = "SELECT * FROM categories WHERE name = '{}'".format(new_cat)
            cursor.execute(look_for_existing_cat)
            result = cursor.fetchone()
            if result:
                return json_resp("ERROR", "Category already exists", 200, "CAT_ID", result["id"])
            else:
                create_new_cat = "INSERT INTO categories (name) VALUES ('{}')".format(new_cat)
                cursor.execute(create_new_cat)
                connection.commit()
                new_id = cursor.lastrowid
                return json_resp("SUCCESS", "", 201, "CAT_ID", new_id)
    except:
        return intErr()


@delete('/category/<id:int>')
def delete_category(id):
    try:
        with connection.cursor() as cursor:
            find_cat = "SELECT * FROM categories WHERE id = {}".format(id)
            cursor.execute(find_cat)
            cat_to_delete = cursor.fetchone()
            if cat_to_delete:
                delete_cat = "DELETE FROM categories WHERE id = {}".format(id)
                cursor.execute(delete_cat)
                connection.commit()
                return json_resp("SUCCESS", "", 200)
            else:
                return json_resp("ERROR", "Category not found", 404)
    except:
        return intErr()


@get('/categories')
def load_categories():
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM categories"
            cursor.execute(sql)
            categories = cursor.fetchall()
            return json_resp("SUCCESS", "", 200, "CATEGORIES", categories)
    except:
        return intErr()


@get('/products')
def load_products():
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM products"
            cursor.execute(sql)
            products = cursor.fetchall()
            return json_resp("SUCCESS", "", 200, "PRODUCTS", products)
    except:
        return intErr()


@post('/product')
def product():
    try:
        id = int(request.forms.get('id')) if request.forms.get('id') else None
        category = int(request.forms.get("category"))
        price = float(request.forms.get("price"))
    except:
        return json_resp("ERROR", "One or more invalid entries", 400)
    product_dict = {
        "category": category,
        "title": request.forms.get("title"),
        "price": price,
        "description": request.forms.get('desc'),
        "favorite": 1 if request.forms.get('favorite') == "on" else 0,
        "img_url": request.forms.get('img_url'),
        "id": id
    }
    if product_dict["id"]:
        return edit_product(product_dict)
    else:
        return add_product(product_dict)


def add_product(product_dict):
    column_names = ', '.join([k for k in product_dict.keys() if k != "id"])
    column_values = ', '.join(
        [str(v) if type(v) != str else '"{}"'.format(v) for k, v in product_dict.items() if k != "id"])
    try:
        with connection.cursor() as cursor:
            confirm_cat = "SELECT * FROM categories WHERE id = {}".format(product_dict["category"])
            cursor.execute(confirm_cat)
            if not cursor.fetchone():
                return json_resp("ERROR", "Category not found", 404)
            else:
                sql = "INSERT INTO products ({}) VALUES ({})".format(column_names, column_values)
                cursor.execute(sql)
                connection.commit()
                new_id = cursor.lastrowid
                return json_resp("SUCCESS", "", 201, "PRODUCT_ID", new_id)
    except:
        return intErr()


def edit_product(product_dict):
    updates = ', '.join(
        ["{} = {}".format(k, str(v)) if type(v) != str else "{} = '{}'".format(k, v) for k, v in product_dict.items() if
         k != "id"])
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE products SET {} WHERE id = {}".format(updates, product_dict["id"])
            cursor.execute(sql)
            connection.commit()
            return json_resp("SUCCESS", "", 201, "PRODUCT_ID", product_dict["id"])
    except:
        return intErr()


@get('/product/<id:int>')
def get_product(id):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM products WHERE id = {}".format(id)
            cursor.execute(sql)
            result = cursor.fetchone()
            if not result:
                return json_resp("ERROR", "Product not found", 404)
            return json_resp("SUCCESS", "", 200, "PRODUCT", result)
    except:
        return intErr()


@delete('/product/<id:int>')
def delete_product(id):
    try:
        with connection.cursor() as cursor:
            find_prod = "SELECT * FROM products WHERE id = {}".format(id)
            cursor.execute(find_prod)
            prod_to_delete = cursor.fetchone()
            if prod_to_delete:
                delete_prod = "DELETE FROM products WHERE id = {}".format(id)
                cursor.execute(delete_prod)
                connection.commit()
                return json_resp("SUCCESS", "", 200)
            else:
                return json_resp("ERROR", "Product not found", 404)
    except:
        return intErr()


@get('/category/<id:int>/products')
def products_by_category(id):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM products WHERE category = {}".format(id)
            cursor.execute(sql)
            products = cursor.fetchall()
            if not products:
                find_cat = "SELECT * FROM categories WHERE id = {}".format(id)
                cursor.execute(find_cat)
                cat = cursor.fetchone()
                if not cat:
                    return json_resp("ERROR", "Category not found", 404)
            return json_resp("SUCCESS", "", 200, "PRODUCTS", reorder(products))
    except:
        return intErr()


def reorder(prod_list):
    favorites = [prod for prod in prod_list if prod["favorite"] == 1]
    nonfavorites = [prod for prod in prod_list if prod["favorite"] != 1]
    favorites.sort(key=lambda prod: prod["id"])
    nonfavorites.sort(key=lambda prod: prod["id"])
    return favorites + nonfavorites


@get('/settings')
@post('/settings')
def settings():
    if request.method == "GET":
        return get_settings()
    else:
        return change_settings()


def get_settings():
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM store_info"
            cursor.execute(sql)
            result = cursor.fetchone()
            return json_resp("SUCCESS", "", 200, "INFO", result)
    except:
        return intErr()


def change_settings():
    new_name = request.forms.get('name')
    new_email = request.forms.get('email')
    if not new_name or not new_email:
        return json_resp("ERROR", "One of the fields is invalid", 400)
    try:
        with connection.cursor() as cursor:
            print('connected and changing existing settings')
            sql = "UPDATE store_info SET name = '{}', email = '{}' WHERE enforce_one_row = 'only'".format(new_name,
                                                                                                          new_email)
            cursor.execute(sql)
            print('executed ' + sql)
            connection.commit()
            return json_resp("SUCCESS", "", 201)
    except:
        return intErr()


run(host='localhost', port=7000)
