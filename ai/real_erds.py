"""Real-world ERDs ("ERD orang") used as the model's gold eval set.

Foreign-key structures of well-known sample / textbook schemas (Sakila,
Northwind, plus classic library / hospital / school / online-shop systems).
Each is (entities, fk_pairs) with fk_pairs as index pairs into entities — the
same relationship-graph the ERD-Chen ordering decision is made on.
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

REAL_ERDS = {
    "northwind": (_NORTHWIND_E, _NORTHWIND),
    "library": (_LIBRARY_E, _LIBRARY),
    "hospital": (_HOSPITAL_E, _HOSPITAL),
    "school": (_SCHOOL_E, _SCHOOL),
    "online_shop": (_SHOP_E, _SHOP),
    "sakila": (_SAKILA_E, _SAKILA),
}
