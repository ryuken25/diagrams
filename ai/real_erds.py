"""Real-world ERDs ("ERD orang") — the model's gold eval set (never trained on).

Foreign-key structures of well-known sample / textbook / CMS schemas, each
reduced to its core entities so it matches the size of the user's own diagrams
(a handful of entities, sparse FK graph). Each entry is (entities, fk_pairs)
with fk_pairs as *index* pairs into entities — the exact relationship-graph the
ERD-Chen ring-ordering decision is made on. These double as the
``reference_diagrams/`` corpus (see ``ai/dump_reference.py``).

Sources: MySQL/PostgreSQL sample DBs (Sakila, world, employees), Microsoft
Northwind, Chinook, classicmodels (Eclipse/MySQL), WordPress & Moodle core, and
classic textbook library/hospital/school/POS/inventory/HR/university schemas.
"""
from __future__ import annotations


def _pairs(entities, fks):
    idx = {e: i for i, e in enumerate(entities)}
    return [(min(idx[a], idx[b]), max(idx[a], idx[b])) for a, b in fks]


_NORTHWIND_E = ["customers", "orders", "order_details", "products",
                "categories", "suppliers", "employees", "shippers"]
_NORTHWIND = _pairs(_NORTHWIND_E, [
    ("customers", "orders"), ("employees", "orders"), ("shippers", "orders"),
    ("orders", "order_details"), ("products", "order_details"),
    ("categories", "products"), ("suppliers", "products")])

_LIBRARY_E = ["member", "loan", "book", "author", "book_author", "category",
              "publisher"]
_LIBRARY = _pairs(_LIBRARY_E, [
    ("member", "loan"), ("book", "loan"), ("category", "book"),
    ("publisher", "book"), ("book", "book_author"), ("author", "book_author")])

_HOSPITAL_E = ["patient", "doctor", "department", "appointment",
               "prescription", "medicine", "room"]
_HOSPITAL = _pairs(_HOSPITAL_E, [
    ("patient", "appointment"), ("doctor", "appointment"),
    ("doctor", "department"), ("appointment", "prescription"),
    ("prescription", "medicine"), ("patient", "room"),
    ("department", "room")])

_SCHOOL_E = ["student", "enrollment", "course", "teacher", "department",
             "classroom", "semester"]
_SCHOOL = _pairs(_SCHOOL_E, [
    ("student", "enrollment"), ("course", "enrollment"),
    ("teacher", "course"), ("department", "teacher"),
    ("course", "semester"), ("classroom", "course")])

_SHOP_E = ["user", "cart", "cart_item", "product", "category", "order",
           "order_item", "payment"]
_SHOP = _pairs(_SHOP_E, [
    ("user", "cart"), ("cart", "cart_item"), ("product", "cart_item"),
    ("category", "product"), ("user", "order"), ("order", "order_item"),
    ("product", "order_item"), ("order", "payment")])

_SAKILA_E = ["country", "city", "address", "customer", "store", "staff",
             "inventory", "rental", "payment"]
_SAKILA = _pairs(_SAKILA_E, [
    ("country", "city"), ("city", "address"), ("address", "customer"),
    ("address", "store"), ("store", "staff"), ("customer", "rental"),
    ("staff", "rental"), ("rental", "payment"), ("store", "inventory")])

# --- added reference schemas (same small, sparse character) ------------------
_CHINOOK_E = ["artist", "album", "track", "genre", "invoice_line", "invoice",
              "customer", "employee"]
_CHINOOK = _pairs(_CHINOOK_E, [
    ("artist", "album"), ("album", "track"), ("genre", "track"),
    ("track", "invoice_line"), ("invoice", "invoice_line"),
    ("customer", "invoice"), ("employee", "customer")])

_CLASSICMODELS_E = ["offices", "employees", "customers", "orders",
                    "orderdetails", "products", "productlines", "payments"]
_CLASSICMODELS = _pairs(_CLASSICMODELS_E, [
    ("offices", "employees"), ("employees", "customers"),
    ("customers", "orders"), ("orders", "orderdetails"),
    ("products", "orderdetails"), ("productlines", "products"),
    ("customers", "payments")])

_EMPLOYEES_E = ["employees", "departments", "dept_emp", "dept_manager",
                "titles", "salaries"]
_EMPLOYEES = _pairs(_EMPLOYEES_E, [
    ("employees", "dept_emp"), ("departments", "dept_emp"),
    ("employees", "dept_manager"), ("departments", "dept_manager"),
    ("employees", "titles"), ("employees", "salaries")])

_WORLD_E = ["country", "city", "countrylanguage"]
_WORLD = _pairs(_WORLD_E, [("country", "city"), ("country", "countrylanguage")])

_WORDPRESS_E = ["users", "posts", "comments", "postmeta", "term_relationships",
                "term_taxonomy", "terms"]
_WORDPRESS = _pairs(_WORDPRESS_E, [
    ("users", "posts"), ("posts", "comments"), ("posts", "postmeta"),
    ("posts", "term_relationships"), ("term_taxonomy", "term_relationships"),
    ("terms", "term_taxonomy")])

_BLOG_E = ["user", "post", "comment", "category", "tag", "post_tag"]
_BLOG = _pairs(_BLOG_E, [
    ("user", "post"), ("post", "comment"), ("category", "post"),
    ("post", "post_tag"), ("tag", "post_tag")])

_FORUM_E = ["user", "category", "board", "thread", "post"]
_FORUM = _pairs(_FORUM_E, [
    ("category", "board"), ("board", "thread"), ("user", "thread"),
    ("thread", "post"), ("user", "post")])

_SALON_E = ["customer", "service", "slot", "booking", "payment", "staff",
            "booking_log"]
_SALON = _pairs(_SALON_E, [
    ("customer", "booking"), ("service", "booking"), ("slot", "booking"),
    ("booking", "payment"), ("staff", "booking"), ("booking", "booking_log")])

_INVENTORY_E = ["supplier", "category", "product", "warehouse", "stock",
                "purchase_order", "po_item"]
_INVENTORY = _pairs(_INVENTORY_E, [
    ("supplier", "product"), ("category", "product"), ("warehouse", "stock"),
    ("product", "stock"), ("supplier", "purchase_order"),
    ("purchase_order", "po_item"), ("product", "po_item")])

_POS_E = ["customer", "category", "menu_item", "dining_table", "order",
          "order_item", "payment", "staff"]
_POS = _pairs(_POS_E, [
    ("category", "menu_item"), ("customer", "order"), ("dining_table", "order"),
    ("staff", "order"), ("order", "order_item"), ("menu_item", "order_item"),
    ("order", "payment")])

_UNIVERSITY_E = ["department", "program", "student", "course", "section",
                 "enrollment", "instructor", "semester"]
_UNIVERSITY = _pairs(_UNIVERSITY_E, [
    ("department", "program"), ("student", "program"), ("department", "course"),
    ("course", "section"), ("instructor", "section"), ("semester", "section"),
    ("student", "enrollment"), ("section", "enrollment")])

_HR_E = ["department", "position", "employee", "payroll", "attendance",
         "leave_request"]
_HR = _pairs(_HR_E, [
    ("department", "employee"), ("position", "employee"),
    ("employee", "payroll"), ("employee", "attendance"),
    ("employee", "leave_request")])

REAL_ERDS = {
    "northwind": (_NORTHWIND_E, _NORTHWIND),
    "library": (_LIBRARY_E, _LIBRARY),
    "hospital": (_HOSPITAL_E, _HOSPITAL),
    "school": (_SCHOOL_E, _SCHOOL),
    "online_shop": (_SHOP_E, _SHOP),
    "sakila": (_SAKILA_E, _SAKILA),
    "chinook": (_CHINOOK_E, _CHINOOK),
    "classicmodels": (_CLASSICMODELS_E, _CLASSICMODELS),
    "employees": (_EMPLOYEES_E, _EMPLOYEES),
    "world": (_WORLD_E, _WORLD),
    "wordpress": (_WORDPRESS_E, _WORDPRESS),
    "blog": (_BLOG_E, _BLOG),
    "forum": (_FORUM_E, _FORUM),
    "salon": (_SALON_E, _SALON),
    "inventory": (_INVENTORY_E, _INVENTORY),
    "restaurant_pos": (_POS_E, _POS),
    "university": (_UNIVERSITY_E, _UNIVERSITY),
    "hr_payroll": (_HR_E, _HR),
}
