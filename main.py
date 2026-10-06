#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
 HOTEL AKSHARA - BILLING DASHBOARD  (हॉटेल अक्षरा - बिलिंग)
==============================================================
 Single file app: backend + frontend together.

 HOW TO RUN
   1. Install Python 3.8 or newer (https://www.python.org)
   2. Open a terminal / command prompt in this folder
   3. Run:   python main.py
   4. Browser opens automatically at  http://localhost:5000

 HOW IT WORKS
   - Home page = Tables. Tap a table, choose Hotel or Beer Bar menu, add
     items. Many tables can be running at once; each keeps its own order.
   - "Make Bill" on a table creates a SEPARATE bill for Hotel items and
     for Bar items, then frees the table.
   - Reports -> daily combined bill for Hotel and for Bar (printable).
   - Bar items/prices are added in Admin -> Menu Items (Beer Bar filter).

 - No extra packages needed (uses only Python's standard library).
 - All data (menu, bills, settings) is saved in "akshara.db"
   in the same folder. Back up that file to keep your data safe.
 - Default Admin PIN: 1234  (change it in Admin -> Settings)
 - Other phones/PCs on the same Wi-Fi can open the
   "Network" address printed in the terminal.
==============================================================
"""
import csv
import io
import json
import os
import socket
import sqlite3
import threading
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "akshara.db")
LOCK = threading.Lock()


# ------------------------------------------------------------------
#  DEFAULT MENU  (taken from the Hotel Akshara menu card)
# ------------------------------------------------------------------
def P(p):
    return [{"mr": "", "en": "", "p": p}]


def HF(h, f):
    return [{"mr": "हाफ", "en": "Half", "p": h}, {"mr": "फुल", "en": "Full", "p": f}]


def PHF(p, h, f):
    return [{"mr": "प्लेट", "en": "Plate", "p": p},
            {"mr": "हाफ", "en": "Half", "p": h},
            {"mr": "फुल", "en": "Full", "p": f}]


def SB(s, b):
    return [{"mr": "छोटी", "en": "Small", "p": s}, {"mr": "मोठी", "en": "Big", "p": b}]


V, N = "veg", "nonveg"

SEED_MENU = [
    ("थाळी", "Thali", [
        ("अंडा थाळी", "Egg Thali", N, P(180)),
        ("चिकन स्पेशल थाळी", "Chicken Special Thali", N, P(199)),
        ("मटण स्पेशल थाळी", "Mutton Special Thali", N, P(270)),
        ("फिश थाळी", "Fish Thali", N, P(250)),
        ("व्हेज स्पेशल थाळी", "Veg Special Thali", V, P(250)),
        ("राईस प्लेट", "Rice Plate", V, P(120)),
    ]),
    ("सूप (व्हेज)", "Soup (Veg)", [
        ("हॉट ॲण्ड सोअर", "Hot & Sour", V, P(90)),
        ("टोमॅटो सूप", "Tomato Soup", V, P(80)),
        ("कोथिंबीर सूप", "Coriander Soup", V, P(80)),
        ("पालक सूप", "Palak Soup", V, P(90)),
        ("शेवगा सूप", "Shevga Soup", V, P(100)),
    ]),
    ("कंटक्की", "Kantakki", [
        ("चिकन कंटक्की", "Chicken Kantakki", N, HF(270, 500)),
        ("पनीर कंटक्की", "Paneer Kantakki", V, P(200)),
        ("सोयाबिन कंटक्की", "Soyabeen Kantakki", V, P(130)),
        ("गोबी कंटक्की", "Gobi Kantakki", V, P(140)),
    ]),
    ("व्हेज स्नॅक्स स्टार्टर", "Veg Snacks Starter", [
        ("फ्राय पापड", "Fry Papad", V, P(30)),
        ("मसाला पापड", "Masala Papad", V, P(40)),
        ("नागली पापड", "Nageli Papad", V, P(40)),
        ("फिंगर चिप्स", "Finger Chips", V, P(100)),
        ("मटकी फ्राय", "Matki Fry", V, P(100)),
        ("मटकी नमकिन", "Matki Namkin", V, P(120)),
        ("मटकी ड्राय", "Matki Dry", V, P(140)),
        ("चना गार्लिक ड्राय", "Chana Garlic Dry", V, P(100)),
        ("चना फ्राय", "Chana Fry", V, P(110)),
        ("चना ड्राय", "Chana Dry", V, P(130)),
        ("लसुन फ्राय", "Lasun Fry", V, P(120)),
        ("ग्रीन पीस फ्राय", "Green Peas Fry", V, P(110)),
        ("ग्रीन पीस नमकिन", "Green Peas Namkin", V, P(120)),
        ("शेवगा फ्राय", "Shevga Fry", V, P(150)),
        ("सोयाबिन फ्राय", "Soyabeen Fry", V, P(120)),
        ("हराभरा कबाब", "Harabhara Kabab", V, P(150)),
        ("नागली पापड मसाला", "Nageli Papad Masala", V, P(50)),
        ("रोस्टेड पापड", "Roasted Papad", V, P(30)),
        ("रोस्टेड पापड नागली", "Roasted Papad Nageli", V, P(30)),
        ("रोस्टेड मसाला पापड नागली", "Roasted Masala Papad", V, P(30)),
        ("ड्राय शेंगदाणे", "Dry Peanut", V, P(60)),
        ("चना कंटक्की", "Chana Kantakki", V, P(130)),
        ("मसाला शेंगदाणे", "Masala Peanut", V, P(80)),
    ]),
    ("स्नॅक्स (नॉन-व्हेज)", "Snacks (Non-Veg)", [
        ("चिकन फ्राय", "Chicken Fry", N, P(160)),
        ("चिकन ड्राय", "Chicken Dry", N, P(180)),
        ("मटन फ्राय", "Mutton Fry", N, P(200)),
        ("मटन ड्राय", "Mutton Dry", N, P(220)),
        ("बॉईल अंडा", "Boil Egg", N, P(40)),
        ("बॉईल फ्राय", "Boil Fry", N, P(60)),
        ("बॉईल ठेसा", "Boil Thesa", N, P(120)),
        ("बॉईल भुर्जी ग्रेव्ही", "Boil Bhurji Gravy", N, P(120)),
        ("बॉईल भुर्जी", "Boil Bhurji", N, P(100)),
        ("अंडा भुर्जी", "Egg Bhurji", N, P(90)),
        ("ऑम्लेट अंडा", "Egg Omelette", N, P(80)),
        ("चिकन ठेसा", "Chicken Thesa", N, P(160)),
        ("मटन ठेसा", "Mutton Thesa", N, P(200)),
    ]),
    ("मेन कोर्स (व्हेज)", "Main Course (Veg)", [
        ("बैंगन मराठा", "Baingan Maratha", V, PHF(150, 260, 400)),
        ("शेवगा मसाला", "Shevga Masala", V, PHF(140, 250, 400)),
        ("शेवगा मराठा", "Shevga Maratha", V, PHF(150, 270, 530)),
        ("सोयाबिन मसाला", "Soyabeen Masala", V, PHF(120, 200, 400)),
        ("सोयाबिन मराठा", "Soyabeen Maratha", V, PHF(150, 200, 400)),
        ("टोमॅटो चटणी", "Tomato Chatani", V, P(140)),
        ("तवा बेसन", "Tava Besan", V, P(120)),
        ("तडका बेसन", "Tadaka Besan", V, P(130)),
        ("मटकी मसाला", "Matki Masala", V, P(120)),
        ("गोबी मसाला", "Gobi Masala", V, P(120)),
        ("व्हेज कोफ्ता", "Veg Kofta", V, PHF(150, 300, 600)),
        ("पनीर कोफ्ता", "Paneer Kofta", V, PHF(210, 350, 700)),
        ("व्हेज तवा", "Veg Tawa", V, P(130)),
        ("व्हेज ग्रेव्ही", "Veg Gravy", V, P(80)),
        ("ठेसा", "Thesa", V, P(60)),
        ("काजू मसाला", "Kaju Masala", V, P(190)),
        ("काजू करी", "Kaju Kari", V, P(180)),
        ("शाही पनीर", "Shahi Paneer", V, P(200)),
        ("पनीर भुर्जी", "Paneer Bhurji", V, P(180)),
        ("पनीर कढाई", "Paneer Kadai", V, P(170)),
        ("पनीर लाहोरी", "Paneer Lahori", V, P(180)),
        ("काजू पनीर", "Kaju Paneer", V, P(200)),
        ("पनीर टिक्का मसाला", "Paneer Tikka Masala", V, P(200)),
        ("पनीर चटपटा मसाला", "Paneer Chatpata Masala", V, P(200)),
        ("पनीर मसाला", "Paneer Masala", V, P(160)),
        ("पनीर बटर मसाला", "Paneer Butter Masala", V, P(180)),
        ("पनीर मटर मसाला", "Paneer Matar Masala", V, P(180)),
        ("पालक बटर पनीर मसाला", "Palak Butter Paneer Masala", V, P(200)),
        ("पालक पनीर मसाला", "Palak Paneer Masala", V, P(180)),
        ("व्हेज मराठा", "Veg Maratha", V, P(150)),
        ("मिक्स व्हेज", "Mix Veg", V, P(180)),
        ("व्हेज कोल्हापुरी", "Veg Kolhapuri", V, P(160)),
        ("व्हेज भुना", "Veg Bhuna", V, P(150)),
        ("व्हेज कढाई", "Veg Kadai", V, P(180)),
        ("व्हेज पटियाला", "Veg Patiyala", V, P(180)),
        ("दाल फ्राय", "Dal Fry", V, P(120)),
        ("दाल कोल्हापुरी", "Dal Kolhapuri", V, P(150)),
        ("दाल मखनी", "Dal Makhani", V, P(130)),
        ("दाल तडका", "Dal Tadka", V, P(130)),
        ("आलू मटर", "Aalu Matar", V, P(130)),
        ("आलू गोबी", "Aalu Gobi", V, P(130)),
        ("दम आलू", "Dum Aalu", V, P(150)),
        ("ग्रीन पीस मसाला", "Green Peas Masala", V, P(140)),
        ("चना मसाला", "Chana Masala", V, P(120)),
        ("शेव भाजी कोल्हापुरी", "Shev Bhaji Kolhapuri", V, P(140)),
        ("मलाई कोफ्ता", "Malai Kofta", V, P(180)),
        ("बैंगन मसाला", "Baingan Masala", V, P(130)),
        ("बैंगन भर्ता", "Baingan Bharta", V, P(140)),
        ("पनीर लाजवाब", "Paneer Lajawab", V, P(230)),
        ("व्हेज कस्तुरी मसाला", "Veg Kasturi Masala", V, P(200)),
        ("पनीर अफगाणी मसाला", "Paneer Afghani Masala", V, P(240)),
        ("स्पे. पनीर कराची मसाला", "Special Paneer Karachi Masala", V, P(220)),
        ("पनीर महाराजा मसाला", "Paneer Maharaja Masala", V, P(250)),
        ("मेथी मसाला", "Methi Masala", V, P(130)),
        ("लसुन मेथी", "Lasun Methi", V, P(140)),
        ("लसुन तडका", "Lasun Tadka", V, P(50)),
        ("पनीर लंबा", "Paneer Lamba", V, P(230)),
        ("दूध मेथी", "Milk Methi", V, P(140)),
        ("मेथी अंगारा", "Methi Angara", V, P(140)),
    ]),
    ("मेन कोर्स (नॉन-व्हेज)", "Main Course (Non-Veg)", [
        ("मटन मसाला", "Mutton Masala", N, PHF(200, 450, 800)),
        ("मटन मालवणी", "Mutton Malwani", N, PHF(220, 450, 800)),
        ("मटन भुना", "Mutton Bhuna", N, PHF(210, 450, 800)),
        ("मटन मराठा", "Mutton Maratha", N, PHF(250, 450, 800)),
        ("मटन कढाई", "Mutton Kadhai", N, PHF(210, 450, 800)),
        ("चिकन मसाला", "Chicken Masala", N, PHF(160, 310, 600)),
        ("चिकन बटर मसाला", "Chicken Butter Masala", N, PHF(170, 350, 650)),
        ("चिकन कढाई", "Chicken Kadhai", N, PHF(170, 350, 650)),
        ("चिकन मालवणी", "Chicken Malwani", N, PHF(170, 350, 650)),
        ("चिकन मुर्ग मुसल्लम", "Chicken Murg Musallam", N, PHF(220, 350, 800)),
        ("तंदुरी चिकन मसाला", "Tandoori Chicken Masala", N, PHF(220, 350, 800)),
        ("चिकन लाहोरी कबाब ग्रेव्ही", "Chicken Lahori Kabab Gravy", N, PHF(220, 350, 800)),
        ("चॉईस ऑफ चिकन कबाब मसाला", "Choice of Chicken Kabab Masala", N, PHF(210, 350, 800)),
        ("बटर तंदुरी चिकन मसाला", "Butter Tandoori Chicken Masala", N, PHF(210, 410, 800)),
        ("चिकन मुगलाई", "Chicken Mughlai", N, PHF(220, 430, 850)),
        ("चिकन महाराजा", "Chicken Maharaja", N, PHF(210, 410, 800)),
        ("चिकन लपेटा", "Chicken Lapeta", N, PHF(220, 410, 800)),
        ("तंदुरी चिकन मुगलाई", "Tandoori Chicken Mughlai", N, PHF(230, 430, 850)),
        ("अंडा करी", "Egg Curry", N, PHF(120, 220, 400)),
        ("अंडा मसाला", "Egg Masala", N, PHF(140, 260, 510)),
        ("चिकन पालक मसाला", "Chicken Palak Masala", N, PHF(170, 330, 610)),
        ("मटन पालक मसाला", "Mutton Palak Masala", N, PHF(210, 410, 800)),
        ("नॉनव्हेज ग्रेव्ही", "Non-Veg Gravy", N, P(80)),
    ]),
    ("राईस (व्हेज)", "Rice (Veg)", [
        ("प्लेन राईस", "Plain Rice", V, HF(60, 120)),
        ("जिरा राईस", "Jeera Rice", V, HF(60, 120)),
        ("जिरा गार्लिक राईस", "Jeera Garlic Rice", V, HF(70, 130)),
        ("स्टीम राईस", "Steam Rice", V, HF(50, 100)),
        ("मसाला राईस", "Masala Rice", V, P(150)),
        ("व्हेज पुलाव", "Veg Pulav", V, P(160)),
        ("व्हेज बिर्याणी", "Veg Biryani", V, P(150)),
        ("पनीर बिर्याणी", "Paneer Biryani", V, P(200)),
        ("दाल खिचडी", "Dal Khichadi", V, P(150)),
        ("तडका दाल खिचडी", "Tadaka Dal Khichadi", V, P(160)),
        ("बटर दाल खिचडी", "Butter Dal Khichadi", V, P(170)),
        ("कर्ड राईस", "Curd Rice", V, P(150)),
    ]),
    ("राईस / बिर्याणी (नॉन-व्हेज)", "Rice / Biryani (Non-Veg)", [
        ("अंडा बिर्याणी", "Egg Biryani", N, P(150)),
        ("अंडा फ्राय राईस", "Egg Fried Rice", N, P(150)),
        ("मटन बिर्याणी", "Mutton Biryani", N, P(200)),
        ("मटन दम बिर्याणी", "Mutton Dum Biryani", N, P(200)),
        ("मटन हैद्राबादी दम बिर्याणी", "Mutton Hyderabadi Dum Biryani", N, P(230)),
        ("चिकन बिर्याणी", "Chicken Biryani", N, P(180)),
        ("चिकन दम बिर्याणी", "Chicken Dum Biryani", N, P(190)),
        ("चिकन हैद्राबादी दम बिर्याणी", "Chicken Hyderabadi Dum Biryani", N, P(200)),
    ]),
    ("रोटी", "Roti", [
        ("तंदुरी रोटी", "Tandoori Roti", V, P(15)),
        ("बटर तंदुरी रोटी", "Butter Tandoori Roti", V, P(25)),
        ("चपाती", "Chapati", V, P(15)),
        ("बटर चपाती", "Butter Chapati", V, P(25)),
        ("बाजरी भाकरी", "Bajri Bhakri", V, P(25)),
        ("ज्वारी भाकरी", "Jwari Bhakri", V, P(25)),
        ("बटर ज्वारी / बाजरी", "Butter Bajri / Jwari", V, P(30)),
        ("चीज रोटी", "Cheese Roti", V, P(30)),
        ("बीट रोटी", "Beet Roti", V, P(20)),
    ]),
    ("रायता / सलाड", "Raita / Salad", [
        ("दही वाटी", "Curd Plate", V, P(40)),
        ("ग्रीन सलाड", "Green Salad", V, P(40)),
        ("मिक्स रायता", "Mix Raita", V, P(60)),
        ("टोमॅटो सलाड", "Tomato Salad", V, P(30)),
        ("काकडी सलाड", "Kakadi Salad", V, P(30)),
    ]),
    ("शीतपेय", "Cold Drinks", [
        ("मिनरल वॉटर", "Mineral Water", V, P(20)),
        ("कोल्ड्रिंक", "Cold Drink", V, SB(25, 60)),
        ("कोल्ड्रिंक २०० एम.एल.", "Cold Drink 200 ml", V, P(25)),
        ("स्प्राईट", "Sprite", V, SB(25, 50)),
        ("स्प्राईट २०० एम.एल.", "Sprite 200 ml", V, P(25)),
        ("सोडा २५० एम.एल.", "Soda 250 ml", V, P(25)),
        ("माझा", "Maaza", V, P(25)),
    ]),
    ("बाहेरून आणलेले बनवून", "Outside Item Cooking", [
        ("बाहेरून आणलेले चिकन बनवून", "Outside Chicken Cooking", N, P(450)),
        ("बाहेरून आणलेले मटन बनवून", "Outside Mutton Cooking", N, P(450)),
        ("बाहेरून आणलेले फिश बनवून", "Outside Fish Cooking", N, P(400)),
    ]),
]

# Bar menu (liquor). NOTE: prices are only typical/indicative starting values -
# check and edit them in Admin -> Menu Items -> Beer Bar before real use.
def _r(x, step):
    return int(round(x / float(step)) * step)


def SP(p60, full):
    """Spirit sold by the peg or bottle: 30 ml / 60 ml / Quarter / Half / Full."""
    return [{"mr": "३० मि.ली.", "en": "30 ml", "p": _r(p60 * 0.55, 5)},
            {"mr": "६० मि.ली.", "en": "60 ml", "p": p60},
            {"mr": "क्वार्टर", "en": "Quarter", "p": _r(full * 0.28, 10)},
            {"mr": "हाफ", "en": "Half", "p": _r(full * 0.54, 10)},
            {"mr": "फुल", "en": "Full", "p": full}]


def GB(glass, bottle):
    return [{"mr": "ग्लास", "en": "Glass", "p": glass}, {"mr": "बाटली", "en": "Bottle", "p": bottle}]


SEED_BAR_MENU = [
    ("बियर", "Beer", [
        ("किंगफिशर स्ट्राँग", "Kingfisher Strong", V, P(230)),
        ("किंगफिशर प्रीमियम", "Kingfisher Premium", V, P(210)),
        ("किंगफिशर अल्ट्रा", "Kingfisher Ultra", V, P(280)),
        ("बडवायझर", "Budweiser", V, P(260)),
        ("टुबर्ग स्ट्राँग", "Tuborg Strong", V, P(220)),
        ("टुबर्ग ग्रीन", "Tuborg Green", V, P(200)),
        ("कार्ल्सबर्ग", "Carlsberg", V, P(250)),
        ("हायनेकेन", "Heineken", V, P(280)),
        ("कोरोना एक्स्ट्रा", "Corona Extra", V, P(350)),
        ("बिरा ९१", "Bira 91", V, P(250)),
        ("नॉकआउट स्ट्राँग", "Knockout Strong", V, P(200)),
        ("हेवर्ड्स ५०००", "Haywards 5000", V, P(190)),
    ]),
    ("व्हिस्की", "Whisky", [
        ("रॉयल स्टॅग", "Royal Stag", V, SP(150, 1800)),
        ("इम्पिरियल ब्ल्यू", "Imperial Blue", V, SP(130, 1500)),
        ("ऑफिसर्स चॉईस", "Officer's Choice", V, SP(110, 1200)),
        ("मॅकडॉवेल्स नं.१", "McDowell's No.1", V, SP(130, 1500)),
        ("ब्लेंडर्स प्राईड", "Blenders Pride", V, SP(220, 2500)),
        ("अँटिक्विटी ब्ल्यू", "Antiquity Blue", V, SP(320, 3800)),
        ("सिग्नेचर", "Signature", V, SP(230, 2700)),
        ("१०० पायपर्स", "100 Pipers", V, SP(280, 3300)),
        ("डायरेक्टर्स स्पेशल", "Director's Special", V, SP(110, 1200)),
        ("बॅगपायपर", "Bagpiper", V, SP(100, 1100)),
        ("रॉयल चॅलेंज", "Royal Challenge", V, SP(170, 2000)),
        ("टीचर्स हायलँड क्रीम", "Teacher's Highland Cream", V, SP(260, 3000)),
        ("व्हॅट ६९", "Vat 69", V, SP(240, 2800)),
        ("रॉकफोर्ड रिझर्व्ह", "Rockford Reserve", V, SP(140, 1600)),
    ]),
    ("स्कॉच / प्रीमियम व्हिस्की", "Scotch / Premium Whisky", [
        ("जॉनी वॉकर रेड लेबल", "Johnnie Walker Red Label", V, SP(300, 3600)),
        ("जॉनी वॉकर ब्लॅक लेबल", "Johnnie Walker Black Label", V, SP(480, 5800)),
        ("चिव्हास रीगल १२", "Chivas Regal 12", V, SP(550, 6800)),
        ("बॅलेंटाईन्स फिनेस्ट", "Ballantine's Finest", V, SP(300, 3600)),
        ("ब्लॅक अँड व्हाईट", "Black & White", V, SP(280, 3300)),
        ("जॅक डॅनियल्स", "Jack Daniel's", V, SP(450, 5500)),
        ("जेमसन", "Jameson", V, SP(400, 4800)),
        ("ग्लेनफिडिक १२", "Glenfiddich 12", V, SP(800, 9500)),
        ("मंकी शोल्डर", "Monkey Shoulder", V, SP(650, 7800)),
    ]),
    ("रम", "Rum", [
        ("ओल्ड मंक", "Old Monk", V, SP(130, 1500)),
        ("मॅकडॉवेल्स सेलिब्रेशन", "McDowell's Celebration", V, SP(120, 1400)),
        ("बकार्डी व्हाईट", "Bacardi White", V, SP(170, 2000)),
        ("बकार्डी ब्लॅक", "Bacardi Black", V, SP(180, 2200)),
        ("कॅप्टन मॉर्गन", "Captain Morgan", V, SP(200, 2400)),
        ("कॉन्टेसा", "Contessa", V, SP(110, 1200)),
        ("हर्क्युलिस", "Hercules", V, SP(100, 1100)),
        ("ओल्ड कास्क", "Old Cask", V, SP(120, 1300)),
    ]),
    ("व्हॉडका", "Vodka", [
        ("स्मिरनॉफ", "Smirnoff", V, SP(190, 2200)),
        ("ॲब्सोल्यूट", "Absolut", V, SP(320, 3800)),
        ("मॅजिक मोमेंट्स", "Magic Moments", V, SP(150, 1800)),
        ("रोमानोव्ह", "Romanov", V, SP(130, 1500)),
        ("व्हाईट मिसचीफ", "White Mischief", V, SP(110, 1300)),
        ("एरिस्टॉफ", "Eristoff", V, SP(150, 1800)),
        ("ग्रे गूज", "Grey Goose", V, SP(600, 7500)),
    ]),
    ("ब्रँडी", "Brandy", [
        ("हनी बी", "Honey Bee", V, SP(110, 1200)),
        ("मॅन्शन हाऊस", "Mansion House", V, SP(140, 1600)),
        ("मॅकडॉवेल्स नं.१ ब्रँडी", "McDowell's No.1 Brandy", V, SP(120, 1400)),
        ("ओल्ड ॲडमिरल", "Old Admiral", V, SP(110, 1200)),
        ("मॉर्फियस", "Morpheus", V, SP(180, 2200)),
        ("हेनेसी व्ही.एस.", "Hennessy VS", V, SP(700, 8500)),
    ]),
    ("जिन", "Gin", [
        ("बॉम्बे सफायर", "Bombay Sapphire", V, SP(330, 4000)),
        ("ब्ल्यू रिबँड", "Blue Riband", V, SP(130, 1500)),
        ("गॉर्डन्स", "Gordon's", V, SP(260, 3000)),
        ("टँकरे", "Tanqueray", V, SP(400, 4800)),
        ("ग्रेटर दॅन", "Greater Than", V, SP(220, 2600)),
    ]),
    ("वाईन", "Wine", [
        ("सुला शिराझ", "Sula Shiraz", V, GB(250, 1300)),
        ("सुला कॅबरने सॉव्हिनॉन", "Sula Cabernet Sauvignon", V, GB(250, 1300)),
        ("सुला शेनिन ब्लँक", "Sula Chenin Blanc", V, GB(250, 1300)),
        ("सुला सॉव्हिनॉन ब्लँक", "Sula Sauvignon Blanc", V, GB(270, 1400)),
        ("सुला रोझे", "Sula Rose", V, GB(250, 1300)),
        ("सुला ब्रूट स्पार्कलिंग", "Sula Brut Sparkling", V, [{"mr": "बाटली", "en": "Bottle", "p": 2200}]),
        ("ग्रोव्हर झांपा ला रिझर्व्ह", "Grover Zampa La Reserve", V, GB(300, 1700)),
        ("फ्रॅटेली सेट्टे", "Fratelli Sette", V, GB(330, 1800)),
        ("पोर्ट वाईन", "Port Wine", V, GB(150, 800)),
    ]),
    ("टकीला / लिक्वर", "Tequila & Liqueur", [
        ("होजे क्युर्व्हो गोल्ड", "Jose Cuervo Gold", V, SP(350, 4200)),
        ("बेलीज", "Baileys", V, SP(300, 3600)),
        ("काहलुआ", "Kahlua", V, SP(280, 3400)),
        ("येगरमाइस्टर", "Jagermeister", V, SP(300, 3600)),
    ]),
    ("सोडा / वॉटर / इतर", "Soda / Water / Others", [
        ("सोडा", "Soda", V, P(25)),
        ("मिनरल वॉटर", "Mineral Water (Bar)", V, P(20)),
        ("टॉनिक वॉटर", "Tonic Water", V, P(60)),
        ("कोल्ड्रिंक", "Cold Drink (Bar)", V, P(40)),
        ("स्प्राईट", "Sprite (Bar)", V, P(40)),
        ("रेड बुल", "Red Bull", V, P(125)),
        ("लिंबू सोडा", "Lime Soda", V, P(40)),
        ("बर्फ", "Ice", V, P(20)),
    ]),
]

SECTIONS = ("hotel", "bar")

DEFAULT_SETTINGS = {
    "hotel_mr": "हॉटेल अक्षरा",
    "hotel_en": "Hotel Akshara",
    "tag_mr": "बियर बार ॲण्ड फॅमिली गार्डन रेस्टॉरंट",
    "tag_en": "Beer Bar & Family Garden Restaurant",
    "addr_mr": "",
    "addr_en": "",
    "phone": "9762649902",
    "gstin": "",
    "footer_mr": "धन्यवाद! पुन्हा भेट द्या.",
    "footer_en": "Thank you! Visit again.",
    "paper": "80",
    "table_count": "15",
    "admin_pin": "1234",
}
PUBLIC_SETTING_KEYS = [k for k in DEFAULT_SETTINGS if k != "admin_pin"]


# ------------------------------------------------------------------
#  DATABASE
# ------------------------------------------------------------------
def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    try:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_mr TEXT, name_en TEXT, sort INTEGER DEFAULT 0,
            section TEXT DEFAULT 'hotel');
        CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER, name_mr TEXT, name_en TEXT,
            type TEXT DEFAULT 'veg', variants TEXT,
            active INTEGER DEFAULT 1, sort INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS bills(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT, table_no TEXT, customer TEXT, items TEXT,
            subtotal REAL, discount REAL, total REAL, payment TEXT,
            section TEXT DEFAULT 'hotel');
        CREATE TABLE IF NOT EXISTS orders(
            table_no TEXT PRIMARY KEY, customer TEXT, items TEXT,
            created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE INDEX IF NOT EXISTS idx_bills_created ON bills(created_at);
        """)
        # upgrade databases created before hotel / bar sections existed
        for tbl in ("categories", "bills"):
            cols = [r["name"] for r in con.execute("PRAGMA table_info({})".format(tbl))]
            if "section" not in cols:
                con.execute("ALTER TABLE {} ADD COLUMN section TEXT DEFAULT 'hotel'".format(tbl))
        if con.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            for ci, (cmr, cen, items) in enumerate(SEED_MENU):
                cur = con.execute(
                    "INSERT INTO categories(name_mr,name_en,sort) VALUES(?,?,?)",
                    (cmr, cen, (ci + 1) * 10))
                cid = cur.lastrowid
                for ii, (imr, ien, typ, var) in enumerate(items):
                    con.execute(
                        "INSERT INTO items(category_id,name_mr,name_en,type,variants,active,sort)"
                        " VALUES(?,?,?,?,?,1,?)",
                        (cid, imr, ien, typ, json.dumps(var, ensure_ascii=False), ii))
        # one-time: add the bar categories + items (existing ones are matched by name, never duplicated)
        if not con.execute("SELECT 1 FROM settings WHERE key='bar_menu_seeded'").fetchone():
            prev = con.execute("SELECT COALESCE(MAX(sort),0) FROM categories").fetchone()[0]
            for cmr, cen, items in SEED_BAR_MENU:
                row = con.execute("SELECT id,sort FROM categories WHERE section='bar' AND name_en=?", (cen,)).fetchone()
                if row:
                    cid, prev = row["id"], row["sort"]
                else:
                    prev += 1
                    cid = con.execute("INSERT INTO categories(name_mr,name_en,sort,section) VALUES(?,?,?,'bar')",
                                      (cmr, cen, prev)).lastrowid
                have = {(r["name_en"] or "").lower() for r in con.execute(
                    "SELECT name_en FROM items WHERE category_id=?", (cid,))}
                nxt = con.execute("SELECT COALESCE(MAX(sort),0) FROM items WHERE category_id=?", (cid,)).fetchone()[0]
                for imr, ien, typ, var in items:
                    if ien.lower() in have:
                        continue
                    nxt += 1
                    con.execute("INSERT INTO items(category_id,name_mr,name_en,type,variants,active,sort)"
                                " VALUES(?,?,?,?,?,1,?)", (cid, imr, ien, typ, json.dumps(var, ensure_ascii=False), nxt))
            con.execute("INSERT INTO settings(key,value) VALUES('bar_menu_seeded','1')")
        for k, v in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        con.commit()
    finally:
        con.close()


def get_settings(con):
    return {r["key"]: r["value"] for r in con.execute("SELECT key,value FROM settings")}


def num(x):
    x = float(x or 0)
    return int(x) if x.is_integer() else round(x, 2)


class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def clean_variants(raw):
    out = []
    for v in raw or []:
        if not isinstance(v, dict):
            continue
        p = to_float(v.get("p"), -1)
        if p < 0:
            continue
        out.append({"mr": str(v.get("mr", "")).strip(), "en": str(v.get("en", "")).strip(), "p": num(p)})
    if not out:
        raise ApiError(400, "At least one price is required / किमान एक दर आवश्यक")
    return out


def sec(x):
    return "bar" if x == "bar" else "hotel"


def item_row(r, secmap=None):
    return {"id": r["id"], "category_id": r["category_id"], "name_mr": r["name_mr"],
            "name_en": r["name_en"], "type": r["type"], "active": r["active"],
            "sort": r["sort"], "variants": json.loads(r["variants"] or "[]"),
            "section": (secmap or {}).get(r["category_id"], "hotel")}


def bill_row(r):
    return {"id": r["id"], "created_at": r["created_at"], "table_no": r["table_no"] or "",
            "customer": r["customer"] or "", "items": json.loads(r["items"] or "[]"),
            "subtotal": num(r["subtotal"]), "discount": num(r["discount"]),
            "total": num(r["total"]), "payment": r["payment"], "section": sec(r["section"])}


def clean_lines(raw):
    lines = []
    for it in raw or []:
        if not isinstance(it, dict):
            continue
        qty = int(to_float(it.get("qty"), 0))
        price = to_float(it.get("price"), -1)
        if qty <= 0 or price < 0:
            continue
        lines.append({
            "item_id": it.get("item_id"), "section": sec(it.get("section")),
            "name_mr": str(it.get("name_mr", "")), "name_en": str(it.get("name_en", "")),
            "vmr": str(it.get("vmr", "")), "ven": str(it.get("ven", "")),
            "price": num(price), "qty": qty})
    return lines


def order_row(r):
    items = json.loads(r["items"] or "[]")
    tot = {"hotel": 0.0, "bar": 0.0}
    for l in items:
        tot[sec(l.get("section"))] += l["price"] * l["qty"]
    return {"table_no": r["table_no"], "customer": r["customer"] or "", "items": items,
            "created_at": r["created_at"], "updated_at": r["updated_at"],
            "hotel_total": num(tot["hotel"]), "bar_total": num(tot["bar"]),
            "total": num(tot["hotel"] + tot["bar"]), "count": sum(l["qty"] for l in items)}


def norm_ts(ts):
    ts = str(ts or "").strip()[:16]
    try:
        datetime.strptime(ts, "%Y-%m-%d %H:%M")
    except ValueError:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return ts


def insert_bill(con, lines, section, discount, ts, table_no, customer):
    subtotal = sum(l["price"] * l["qty"] for l in lines)
    discount = min(max(to_float(discount, 0), 0), subtotal)
    cur = con.execute(
        "INSERT INTO bills(created_at,table_no,customer,items,subtotal,discount,total,payment,section)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (ts, str(table_no or "").strip()[:20], str(customer or "").strip()[:60],
         json.dumps(lines, ensure_ascii=False), subtotal, discount, subtotal - discount,
         "cash", section))
    return cur.lastrowid


def summarize(bills):
    s = {"total": 0.0, "count": len(bills),
         "subtotal": 0.0, "discount": 0.0, "hotel": 0.0, "bar": 0.0}
    for b in bills:
        s["total"] += b["total"]
        s["subtotal"] += b["subtotal"]
        s["discount"] += b["discount"]
        s[b["section"]] += b["total"]
    return {k: num(v) for k, v in s.items()}


def agg_items(bills):
    agg = {}
    for b in bills:
        for l in b["items"]:
            key = (l["name_mr"], l["name_en"], l["vmr"], l["ven"], l["price"])
            a = agg.setdefault(key, {"name_mr": l["name_mr"], "name_en": l["name_en"],
                                     "vmr": l["vmr"], "ven": l["ven"], "price": l["price"], "qty": 0})
            a["qty"] += l["qty"]
    out = sorted(agg.values(), key=lambda x: -x["qty"] * x["price"])
    for a in out:
        a["amount"] = num(a["qty"] * a["price"])
    return out


# ------------------------------------------------------------------
#  API
# ------------------------------------------------------------------
def api(method, parts, q, body, pin):
    con = db()
    try:
        settings = get_settings(con)
        is_admin = bool(pin) and pin == settings.get("admin_pin")

        def need_admin():
            if not is_admin:
                raise ApiError(401, "Admin PIN required / ॲडमिन पिन आवश्यक")

        res = parts[0] if parts else ""
        rid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

        # ---------- menu ----------
        if res == "menu" and method == "GET":
            cats = [dict(r) for r in con.execute(
                "SELECT id,name_mr,name_en,sort,COALESCE(section,'hotel') AS section"
                " FROM categories ORDER BY sort,id")]
            secmap = {c["id"]: c["section"] for c in cats}
            items = [item_row(r, secmap) for r in con.execute("SELECT * FROM items ORDER BY sort,id")]
            return 200, {"categories": cats, "items": items}

        # ---------- auth ----------
        if res == "login" and method == "POST":
            if str(body.get("pin", "")) == settings.get("admin_pin"):
                return 200, {"ok": True}
            raise ApiError(401, "Wrong PIN / चुकीचा पिन")

        # ---------- settings ----------
        if res == "settings":
            if method == "GET":
                return 200, {k: settings.get(k, "") for k in PUBLIC_SETTING_KEYS}
            if method == "PUT":
                need_admin()
                for k in PUBLIC_SETTING_KEYS:
                    if k in body:
                        con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                                    (k, str(body[k]).strip()))
                newpin = str(body.get("new_pin", "")).strip()
                if newpin:
                    if len(newpin) < 4:
                        raise ApiError(400, "PIN must be at least 4 characters / पिन किमान ४ अंकी हवा")
                    con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('admin_pin',?)", (newpin,))
                con.commit()
                s2 = get_settings(con)
                return 200, {k: s2.get(k, "") for k in PUBLIC_SETTING_KEYS}

        # ---------- categories ----------
        if res == "categories":
            need_admin()
            if method in ("POST", "PUT"):
                mr = str(body.get("name_mr", "")).strip()
                en = str(body.get("name_en", "")).strip()
                if not mr and not en:
                    raise ApiError(400, "Name required / नाव आवश्यक")
                sort = int(to_float(body.get("sort"), 0))
                section = sec(body.get("section"))
                if method == "POST":
                    cur = con.execute("INSERT INTO categories(name_mr,name_en,sort,section) VALUES(?,?,?,?)",
                                      (mr, en, sort, section))
                    rid = cur.lastrowid
                else:
                    con.execute("UPDATE categories SET name_mr=?,name_en=?,sort=?,section=? WHERE id=?",
                                (mr, en, sort, section, rid))
                con.commit()
                return 200, dict(con.execute("SELECT * FROM categories WHERE id=?", (rid,)).fetchone())
            if method == "DELETE" and rid:
                con.execute("DELETE FROM items WHERE category_id=?", (rid,))
                con.execute("DELETE FROM categories WHERE id=?", (rid,))
                con.commit()
                return 200, {"ok": True}

        # ---------- items ----------
        if res == "items":
            need_admin()
            if method in ("POST", "PUT"):
                mr = str(body.get("name_mr", "")).strip()
                en = str(body.get("name_en", "")).strip()
                if not mr and not en:
                    raise ApiError(400, "Name required / नाव आवश्यक")
                cid = int(to_float(body.get("category_id"), 0))
                if not con.execute("SELECT 1 FROM categories WHERE id=?", (cid,)).fetchone():
                    raise ApiError(400, "Select category / विभाग निवडा")
                typ = "nonveg" if body.get("type") == "nonveg" else "veg"
                active = 1 if body.get("active", 1) else 0
                var = json.dumps(clean_variants(body.get("variants")), ensure_ascii=False)
                if method == "POST":
                    mx = con.execute("SELECT COALESCE(MAX(sort),0)+1 FROM items WHERE category_id=?",
                                     (cid,)).fetchone()[0]
                    cur = con.execute(
                        "INSERT INTO items(category_id,name_mr,name_en,type,variants,active,sort)"
                        " VALUES(?,?,?,?,?,?,?)", (cid, mr, en, typ, var, active, mx))
                    rid = cur.lastrowid
                else:
                    con.execute("UPDATE items SET category_id=?,name_mr=?,name_en=?,type=?,variants=?,active=?"
                                " WHERE id=?", (cid, mr, en, typ, var, active, rid))
                con.commit()
                secmap = {r["id"]: sec(r["section"]) for r in con.execute("SELECT id,section FROM categories")}
                return 200, item_row(con.execute("SELECT * FROM items WHERE id=?", (rid,)).fetchone(), secmap)
            if method == "DELETE" and rid:
                con.execute("DELETE FROM items WHERE id=?", (rid,))
                con.commit()
                return 200, {"ok": True}

        # ---------- open table orders ----------
        if res == "orders":
            tno = (parts[1] if len(parts) > 1 else "").strip()[:20]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            def blank():
                return {"table_no": tno, "customer": "", "items": [], "created_at": now,
                        "updated_at": now, "hotel_total": 0, "bar_total": 0, "total": 0, "count": 0}

            if not tno:
                if method == "GET":
                    return 200, [order_row(r) for r in con.execute("SELECT * FROM orders ORDER BY created_at")]
            else:
                row = con.execute("SELECT * FROM orders WHERE table_no=?", (tno,)).fetchone()
                action = parts[2] if len(parts) > 2 else ""
                if method == "GET":
                    return 200, (order_row(row) if row else blank())
                if method == "PUT":
                    lines = clean_lines(body.get("items"))
                    if not lines:
                        con.execute("DELETE FROM orders WHERE table_no=?", (tno,))
                        con.commit()
                        return 200, blank()
                    customer = str(body.get("customer", "")).strip()[:60]
                    created = row["created_at"] if row else now
                    con.execute("INSERT OR REPLACE INTO orders(table_no,customer,items,created_at,updated_at)"
                                " VALUES(?,?,?,?,?)",
                                (tno, customer, json.dumps(lines, ensure_ascii=False), created, now))
                    con.commit()
                    return 200, order_row(con.execute("SELECT * FROM orders WHERE table_no=?", (tno,)).fetchone())
                if method == "DELETE":
                    con.execute("DELETE FROM orders WHERE table_no=?", (tno,))
                    con.commit()
                    return 200, {"ok": True}
                if method == "POST" and action == "checkout":
                    if not row:
                        raise ApiError(404, "No order on this table / या टेबलवर ऑर्डर नाही")
                    o = order_row(row)
                    ts = norm_ts(body.get("created_at"))
                    disc = body.get("discounts") if isinstance(body.get("discounts"), dict) else {}
                    ids = []
                    for s_ in SECTIONS:  # one separate bill for hotel and one for bar
                        lines = [l for l in o["items"] if sec(l.get("section")) == s_]
                        if lines:
                            ids.append(insert_bill(con, lines, s_, disc.get(s_),
                                                   ts, tno, o["customer"]))
                    con.execute("DELETE FROM orders WHERE table_no=?", (tno,))
                    con.commit()
                    return 200, {"bills": [bill_row(con.execute("SELECT * FROM bills WHERE id=?", (i,)).fetchone())
                                           for i in ids]}

        # ---------- bills ----------
        if res == "bills":
            if method == "POST":
                lines = clean_lines(body.get("items"))
                if not lines:
                    raise ApiError(400, "Bill is empty / बिल रिकामे आहे")
                bid = insert_bill(con, lines, sec(body.get("section")), body.get("discount"),
                                  norm_ts(body.get("created_at")), body.get("table_no"), body.get("customer"))
                con.commit()
                return 200, bill_row(con.execute("SELECT * FROM bills WHERE id=?", (bid,)).fetchone())
            if method == "GET":
                d = q.get("date", datetime.now().strftime("%Y-%m-%d"))
                rows = con.execute("SELECT * FROM bills WHERE created_at LIKE ? ORDER BY created_at DESC, id DESC",
                                   (d + "%",))
                return 200, [bill_row(r) for r in rows]
            if method == "DELETE" and rid:
                need_admin()
                con.execute("DELETE FROM bills WHERE id=?", (rid,))
                con.commit()
                return 200, {"ok": True}

        # ---------- reports ----------
        if res == "report" and method == "GET":
            kind = parts[1] if len(parts) > 1 else "day"
            if kind == "day":
                d = q.get("date", datetime.now().strftime("%Y-%m-%d"))
                bills = [bill_row(r) for r in con.execute(
                    "SELECT * FROM bills WHERE created_at LIKE ?", (d + "%",))]
                out = summarize(bills)
                out["sections"] = {}
                for s_ in SECTIONS:
                    sb = [x for x in bills if x["section"] == s_]
                    sm = summarize(sb)
                    sm["items"] = agg_items(sb)
                    out["sections"][s_] = sm
                return 200, out
            if kind == "month":
                m = q.get("month", datetime.now().strftime("%Y-%m"))
                bills = [bill_row(r) for r in con.execute(
                    "SELECT * FROM bills WHERE created_at LIKE ?", (m + "%",))]
                out = summarize(bills)
                days = {}
                for b in bills:
                    days.setdefault(b["created_at"][:10], []).append(b)
                out["days"] = [dict(date=k, **summarize(v)) for k, v in sorted(days.items())]
                return 200, out

        # ---------- CSV export (any month range, e.g. a whole year) ----------
        if res == "export" and method == "GET":
            this_month = datetime.now().strftime("%Y-%m")
            frm = q.get("from") or q.get("month") or this_month
            to = q.get("to") or frm
            for v in (frm, to):
                try:
                    datetime.strptime(v, "%Y-%m")
                except ValueError:
                    raise ApiError(400, "Invalid month / चुकीचा महिना")
            if frm > to:
                frm, to = to, frm
            only = q.get("section")
            bills = [bill_row(r) for r in con.execute(
                "SELECT * FROM bills WHERE substr(created_at,1,7) BETWEEN ? AND ? ORDER BY created_at,id", (frm, to))]
            if only in SECTIONS:
                bills = [b for b in bills if b["section"] == only]
            buf = io.StringIO()
            w = csv.writer(buf)
            if q.get("kind") == "summary":
                w.writerow(["Month", "Bills", "Hotel Total", "Bar Total", "Discount", "Total"])
                months = {}
                for b in bills:
                    months.setdefault(b["created_at"][:7], []).append(b)
                for k, v in sorted(months.items()):
                    sm = summarize(v)
                    w.writerow([k, sm["count"], sm["hotel"], sm["bar"], sm["discount"], sm["total"]])
                sm = summarize(bills)
                w.writerow(["TOTAL", sm["count"], sm["hotel"], sm["bar"], sm["discount"], sm["total"]])
            else:
                w.writerow(["Bill No", "Date Time", "Section", "Table", "Customer", "Items",
                            "Subtotal", "Discount", "Total"])
                for b in bills:
                    items = "; ".join("{}{} x{} @{}".format(
                        l["name_en"] or l["name_mr"],
                        " (" + (l["ven"] or l["vmr"]) + ")" if (l["ven"] or l["vmr"]) else "",
                        l["qty"], l["price"]) for l in b["items"])
                    w.writerow([b["id"], b["created_at"], "Bar" if b["section"] == "bar" else "Hotel",
                                b["table_no"], b["customer"], items, b["subtotal"], b["discount"], b["total"]])
                sm = summarize(bills)
                w.writerow(["", "", "", "", "", "TOTAL", sm["subtotal"], sm["discount"], sm["total"]])
            data = ("\ufeff" + buf.getvalue()).encode("utf-8")
            name = "akshara-{}-{}{}{}.csv".format(
                "summary" if q.get("kind") == "summary" else "bills", frm,
                "" if frm == to else "_to_" + to, "-" + only if only in SECTIONS else "")
            return 200, data, "text/csv; charset=utf-8", {
                "Content-Disposition": 'attachment; filename="{}"'.format(name)}

        raise ApiError(404, "Not found")
    finally:
        con.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "AksharaBilling/1.0"

    def log_message(self, *args):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def handle_any(self, method):
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        if method == "GET" and path in ("/", "/index.html"):
            return self.send(200, INDEX_HTML, "text/html; charset=utf-8")
        if path == "/favicon.ico":
            return self.send(204, b"", "image/x-icon")
        if not path.startswith("/api/"):
            return self.send(404, {"error": "Not found"})
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        parts = path.strip("/").split("/")[1:]
        body = self.read_body() if method in ("POST", "PUT") else {}
        try:
            with LOCK:
                out = api(method, parts, q, body, self.headers.get("X-Admin-Pin", ""))
            self.send(*out)
        except ApiError as e:
            self.send(e.code, {"error": e.msg})
        except Exception as e:  # pragma: no cover
            self.send(500, {"error": "Server error: {}".format(e)})

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")

    def do_PUT(self):
        self.handle_any("PUT")

    def do_DELETE(self):
        self.handle_any("DELETE")


# ------------------------------------------------------------------
#  FRONTEND (HTML + CSS + JS)
# ------------------------------------------------------------------
INDEX_HTML = r"""<!doctype html>
<html lang="mr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>हॉटेल अक्षरा - बिलिंग</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700;800&family=Yatra+One&display=swap" rel="stylesheet">
<style>
:root{
  --mar:#7a1f1f; --mar2:#9e2b2b; --mar3:#5a1414; --sa:#f08a24; --sa2:#ffb25b;
  --cream:#fbf5ea; --card:#ffffff; --ink:#2b1d14; --mut:#7d6b5d; --line:#eadfce;
  --veg:#1f8a3b; --nv:#c62828; --upi:#0e7fb8; --cash:#1f8a3b; --leaf:#5aa83a;
  --hotel:#e8730c; --hotel2:#ffb25b; --bar:#6d3fd1; --bar2:#a07bf0;
  --sh:0 2px 10px rgba(90,20,20,.08); --sh2:0 8px 28px rgba(90,20,20,.16);
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  font-family:'Mukta','Noto Sans Devanagari','Segoe UI',system-ui,sans-serif;
  color:var(--ink); font-size:15px;
  background:
    radial-gradient(900px 480px at -5% -8%, #ffd9ad 0, transparent 60%),
    radial-gradient(800px 460px at 105% 0%, #dccfff 0, transparent 58%),
    radial-gradient(900px 500px at 50% 115%, #cdeedd 0, transparent 60%),
    var(--cream);
  background-attachment:fixed;
  min-height:100vh;
}
button{font-family:inherit;cursor:pointer}
input,select{font-family:inherit;font-size:15px}
.muted{color:var(--mut)}

/* ---------- header ---------- */
header.top{
  position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  padding:10px 18px;color:#fff;
  background:linear-gradient(110deg,var(--mar3),var(--mar) 45%,var(--mar2));
  box-shadow:0 3px 14px rgba(60,10,10,.3);border-bottom:3px solid var(--sa);
}
.brand{display:flex;align-items:center;gap:12px;min-width:0}
.logo{width:46px;height:46px;border-radius:50%;background:var(--mar3);border:3px solid var(--sa);
  display:grid;place-items:center;flex:none}
.hname{font-family:'Mukta','Noto Sans Devanagari',sans-serif;font-weight:800;font-size:26px;line-height:1.15;color:#ffe2bf}
html[lang=en] .hname{font-family:'Yatra One','Mukta',serif;font-weight:400;font-size:24px;letter-spacing:.3px}
.htag{font-size:12px;opacity:.85}
nav{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
nav button{border:0;background:rgba(255,255,255,.1);color:#fff;padding:8px 16px;border-radius:999px;
  font-weight:600;font-size:15px;transition:.15s}
nav button:hover{background:rgba(255,255,255,.2)}
nav button.on{background:var(--sa);color:#2b1300;box-shadow:0 2px 8px rgba(0,0,0,.25)}
.nbadge{display:inline-block;min-width:20px;padding:0 6px;margin-left:4px;border-radius:999px;background:#fff;color:var(--nv);font-size:12px;font-weight:800;line-height:20px;text-align:center}
.nbadge:empty{display:none}
.hright{display:flex;align-items:center;gap:10px}
.daybox{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);padding:5px 16px;border-radius:12px;text-align:center;line-height:1.15}
.daybox b{display:block;font-size:20px;color:#ffe2bf}
.daybox small{font-size:12px;opacity:.9}
.langbtn{border:2px solid var(--sa);background:transparent;color:#fff;padding:6px 12px;border-radius:10px;font-weight:700}
.langbtn:hover{background:var(--sa);color:#2b1300}

main{padding:16px;max-width:1500px;margin:0 auto}

/* ---------- billing ---------- */
.billing{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:16px;align-items:start}
.billing>*{min-width:0}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:var(--sh);padding:14px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.seg{display:inline-flex;background:#f4ebdd;border-radius:12px;padding:3px}
.seg button{border:0;background:transparent;padding:7px 14px;border-radius:9px;font-weight:600;color:var(--mut);display:flex;align-items:center;gap:6px}
.seg button.on{background:#fff;color:var(--ink);box-shadow:0 1px 4px rgba(0,0,0,.12)}
.search{flex:1;min-width:180px;padding:10px 14px;border:1.5px solid var(--line);border-radius:12px;background:#fffdf9;outline:none}
.search:focus{border-color:var(--sa)}
.cats{display:flex;flex-wrap:wrap;gap:6px;padding:2px 0 10px}
.cats button{flex:none;border:1.5px solid var(--line);background:#fff;padding:4px 11px;border-radius:999px;font-weight:600;font-size:14px;color:var(--mar)}
.cats button.on{background:var(--mar);border-color:var(--mar);color:#fff}
.cats button small{opacity:.7;margin-left:4px}
.grid-wrap{max-height:calc(100vh - 410px);min-height:240px;overflow:auto;padding-right:4px}
.ghead{display:flex;align-items:center;gap:10px;margin:14px 0 8px;color:var(--mar);font-weight:800;font-size:17px}
.ghead:after{content:"";flex:1;height:2px;background:linear-gradient(90deg,var(--sa2),transparent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px}
.card{background:#fffdf9;border:1.5px solid var(--line);border-radius:14px;padding:10px 11px;display:flex;flex-direction:column;gap:8px;transition:.12s;position:relative}
.card.click{cursor:pointer}
.card.click:hover{border-color:var(--sa);transform:translateY(-2px);box-shadow:var(--sh2)}
.card.click:active{transform:scale(.97)}
.ctop{display:flex;gap:7px;align-items:flex-start}
.iname{font-weight:700;line-height:1.2;font-size:15px}
.price{font-weight:800;color:var(--mar);font-size:17px;margin-top:auto}
.vars{display:flex;gap:5px;flex-wrap:wrap;margin-top:auto}
.vars button{flex:1;min-width:52px;border:1.5px solid #f1d9bd;background:#fff6ea;border-radius:10px;padding:4px 4px;line-height:1.1;color:var(--ink)}
.vars button:hover{background:var(--sa);border-color:var(--sa);color:#2b1300}
.vars button small{display:block;font-size:11px;color:var(--mut)}
.vars button:hover small{color:#2b1300}
.vars button b{font-size:14px}
.dot{flex:none;width:14px;height:14px;border:2px solid var(--veg);border-radius:3px;display:inline-grid;place-items:center;margin-top:3px}
.dot:after{content:"";width:6px;height:6px;border-radius:50%;background:var(--veg)}
.dot.nonveg{border-color:var(--nv)}
.dot.nonveg:after{background:var(--nv);border-radius:0;width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-bottom:7px solid var(--nv);background:transparent}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;background:#f4ebdd;color:var(--mut)}

.cart-pane{position:sticky;top:86px;display:flex;flex-direction:column;gap:10px;height:calc(100vh - 172px);min-height:430px;overflow:hidden;border-top:5px solid var(--sa)}
.cart-pane>*{flex:none}
.cart-pane>.lines{flex:1 1 auto;min-height:0}
.cart-pane h3{margin:0;display:flex;align-items:center;justify-content:space-between;color:var(--mar);font-size:20px}
.f2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.fld label{display:block;font-size:12px;color:var(--mut);font-weight:600;margin-bottom:2px}
.fld input,.fld select{width:100%;padding:8px 10px;border:1.5px solid var(--line);border-radius:10px;background:#fffdf9;outline:none}
.fld input:focus,.fld select:focus{border-color:var(--sa)}
.dtrow{display:flex;gap:6px}
.dtrow input{flex:1}
.mini{border:1.5px solid var(--line);background:#fff;border-radius:10px;padding:0 10px;font-weight:600;color:var(--mar);white-space:nowrap}
.mini.on{background:#e9f6ec;border-color:#bfe3c8;color:var(--veg)}
.lines{position:relative;overflow:auto;border-top:1px dashed var(--line);border-bottom:1px dashed var(--line);padding:4px 0}
.empty{color:var(--mut);text-align:center;padding:28px 10px}
.empty svg{opacity:.35;display:block;margin:0 auto 6px}
.line{padding:8px 2px;border-bottom:1px solid #f3eadc}
.line:last-child{border-bottom:0}
.lname{font-weight:700;line-height:1.2}
.lname small{font-weight:600;color:var(--sa);margin-left:4px}
.lctrl{display:flex;align-items:center;gap:6px;margin-top:5px}
.qbtn{width:30px;height:30px;border-radius:9px;border:1.5px solid var(--line);background:#fff;font-size:18px;font-weight:700;color:var(--mar);line-height:1}
.qbtn:hover{background:var(--mar);color:#fff;border-color:var(--mar)}
.qty{min-width:26px;text-align:center;font-weight:800}
.pin{width:78px;padding:5px 7px;border:1.5px solid var(--line);border-radius:8px;text-align:right;background:#fff8ec}
.pin:focus{outline:none;border-color:var(--sa)}
.ltot{margin-left:auto;font-weight:800;min-width:70px;text-align:right}
.x{border:0;background:transparent;color:#b9a99a;font-size:16px;padding:2px 4px}
.x:hover{color:var(--nv)}
.tots{display:flex;flex-direction:column;gap:4px}
.tr{display:flex;justify-content:space-between;align-items:center}
.tr input{width:100px;padding:5px 8px;border:1.5px solid var(--line);border-radius:8px;text-align:right}
.grand{background:linear-gradient(100deg,var(--mar),var(--mar2));color:#fff;border-radius:12px;padding:10px 14px;font-size:18px;font-weight:700}
.grand b{font-size:26px;color:#ffe2bf}
.pay{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.pay button{border:2px solid var(--line);background:#fff;border-radius:12px;padding:10px;font-weight:700;font-size:16px;display:flex;align-items:center;justify-content:center;gap:8px;color:var(--mut)}
.pay button.on.cash{border-color:var(--cash);background:#e9f6ec;color:var(--cash)}
.pay button.on.upi{border-color:var(--upi);background:#e3f3fb;color:var(--upi)}
.acts{display:grid;grid-template-columns:1fr;gap:8px}
.btn{border:0;border-radius:12px;padding:11px 16px;font-weight:700;font-size:16px;background:#f1e7d8;color:var(--ink);text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px}
.btn.pri{background:linear-gradient(100deg,var(--sa),#e57412);color:#2b1300;box-shadow:0 3px 10px rgba(240,138,36,.35)}
.btn.pri:hover{filter:brightness(1.05)}
.btn.dark{background:var(--mar);color:#fff}
.btn:disabled{opacity:.55;cursor:not-allowed}
.ghost{border:1.5px solid var(--line);background:#fff;border-radius:10px;padding:8px 14px;font-weight:600;color:var(--mar)}
.ghost:hover{border-color:var(--mar)}
.danger{color:var(--nv)!important}
.fab{display:none}


/* ---------- tables (home) ---------- */
.tstats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px}
.tstat{border-radius:16px;padding:12px 16px;color:#fff;position:relative;overflow:hidden;box-shadow:var(--sh)}
.tstat span{font-size:14px;font-weight:600;opacity:.95}
.tstat b{display:block;font-size:30px;line-height:1.15}
.tstat:after{content:"";position:absolute;right:-18px;top:-22px;width:90px;height:90px;border-radius:50%;background:rgba(255,255,255,.15)}
.ts1{background:linear-gradient(120deg,#e4501f,#ff9a3c)}
.ts2{background:linear-gradient(120deg,#0a5f8c,#26a6df)}
.ts3{background:linear-gradient(120deg,#16692d,#3fbf63)}
.runbox{margin-bottom:14px;border-top:5px solid var(--sa)}
.runbox h3{margin:0 0 10px;color:var(--mar);font-size:19px;display:flex;align-items:center;gap:8px}
.runlist{display:flex;gap:10px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:14px;padding:8px 14px;font-weight:700;color:#fff;
  background:linear-gradient(120deg,#e4501f,#ff9a3c);box-shadow:0 3px 10px rgba(228,80,31,.3);text-align:left;line-height:1.3}
.chip small{display:block;font-weight:600;opacity:.9;font-size:12px}
.chip .cn{font-size:22px;font-weight:800}
.chip:hover{filter:brightness(1.06);transform:translateY(-1px)}
.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}
.tcard{border-radius:18px;padding:12px 14px;min-height:122px;display:flex;flex-direction:column;justify-content:space-between;text-align:left;
  border:2px solid transparent;transition:.12s;font-size:14px}
.tcard:hover{transform:translateY(-3px);box-shadow:var(--sh2)}
.tcard .tno{font-size:34px;font-weight:800;line-height:1}
.tcard .tlab{font-size:12px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;opacity:.8}
.tcard.free{background:linear-gradient(145deg,#f3fcf5,#d9f2e0);border-color:#b4dfc0;color:#17682e}
.tcard.on{background:linear-gradient(145deg,#ff9a3c,#e4501f);color:#fff;box-shadow:0 6px 18px rgba(228,80,31,.35)}
.tcard .trow{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.tpill{background:rgba(255,255,255,.25);border-radius:999px;padding:2px 9px;font-weight:700;font-size:13px}
.tcard .tamt{font-size:20px;font-weight:800}
.tcard .tmeta{font-size:12px;opacity:.92}

/* ---------- order screen ---------- */
.ohead{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.otitle{font-size:26px;font-weight:800;color:var(--mar);margin-right:6px}
.otitle span{display:inline-block;background:linear-gradient(120deg,#e4501f,#ff9a3c);color:#fff;border-radius:12px;padding:0 14px;margin-left:4px}
.strip{display:flex;flex-wrap:wrap;gap:8px;flex:1;min-width:200px;padding:2px}
.strip .chip{flex:none;padding:5px 12px;border-radius:12px}
.strip .chip .cn{font-size:18px}
.strip .chip.cur{outline:3px solid var(--mar);outline-offset:1px}
.btn.cancelT{background:#fde8e8;color:#b42318;border:1.5px solid #f5b5b0;padding:9px 16px}
.btn.cancelT:hover{background:#fbd3d0}
.dl{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.dlbox{border:1.5px solid var(--line);border-radius:14px;padding:12px 14px;background:#fffdf9}
.dlbox h4{margin:0 0 8px;color:var(--mar)}
.dlrow{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.dlrow label{display:flex;flex-direction:column;font-size:12px;font-weight:600;color:var(--mut);gap:2px}
.dlrow input,.dlrow select,.ph select{padding:8px 10px;border:1.5px solid var(--line);border-radius:10px;background:#fff;font-size:15px}
.dlbtns{display:flex;gap:8px;flex-wrap:wrap}
.newtbl{padding:8px 10px;border:2px dashed var(--sa);border-radius:12px;background:#fff8ec;font-weight:700;color:#a4520a}
.secsw{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.secsw button{border:0;border-radius:14px;padding:12px;font-weight:800;font-size:18px;color:#fff;opacity:.5;transition:.15s;display:flex;align-items:center;justify-content:center;gap:8px}
.secsw button.hotel{background:linear-gradient(110deg,#e4501f,#ffa043)}
.secsw button.bar{background:linear-gradient(110deg,#5a2fc0,#a47cf3)}
.secsw button.on{opacity:1;box-shadow:0 6px 16px rgba(0,0,0,.25);transform:translateY(-1px)}
.menu.sec-hotel{border-top:5px solid var(--hotel)}
.menu.sec-bar{border-top:5px solid var(--bar)}
.menu.sec-bar .cats button.on{background:var(--bar);border-color:var(--bar)}
.menu.sec-bar .cats button{color:var(--bar)}
.menu.sec-bar .cats button.on{color:#fff}
.menu.sec-bar .ghead{color:var(--bar)}
.menu.sec-bar .price,.menu.sec-bar .vars b{color:var(--bar)}
.menu.sec-bar .card.click:hover{border-color:var(--bar2)}
.menu.sec-bar .vars button{background:#f4efff;border-color:#ddd0fb}
.menu.sec-bar .vars button:hover{background:var(--bar);border-color:var(--bar);color:#fff}
.menu.sec-bar .vars button:hover small,.menu.sec-bar .vars button:hover b{color:#fff}
.lsec{display:flex;justify-content:space-between;align-items:center;margin:8px 0 2px;padding:5px 10px;border-radius:10px;color:#fff;font-weight:800;font-size:14px}
.lsec.hotel{background:linear-gradient(110deg,#e4501f,#ffa043)}
.lsec.bar{background:linear-gradient(110deg,#5a2fc0,#a47cf3)}
.line.flash{animation:flash .8s ease-out}
@keyframes flash{from{background:#fff0c9}to{background:transparent}}
.cinput{width:100%;padding:8px 10px;border:1.5px solid var(--line);border-radius:10px;background:#fffdf9;outline:none}
.cinput:focus{border-color:var(--sa)}
.empty .btn{margin-top:10px}

/* ---------- checkout ---------- */
.cosec{border-radius:14px;overflow:hidden;border:1.5px solid var(--line);margin-bottom:10px}
.cosec .lsec{margin:0;border-radius:0;font-size:15px}
.cosec .cob{padding:8px 12px}
.corow{display:flex;justify-content:space-between;gap:8px;padding:2px 0;font-size:14px}
.corow.sm{color:var(--mut);font-size:13px}
.cosec input{width:110px;padding:5px 8px;border:1.5px solid var(--line);border-radius:8px;text-align:right}
.cosec .net{font-weight:800;font-size:17px;border-top:1px dashed var(--line);margin-top:4px;padding-top:4px}
.note{background:#fff6e0;border:1px solid #f5d98e;color:#8a5a00;border-radius:10px;padding:7px 10px;font-size:13px;margin-bottom:10px}

/* ---------- day bills (reports) ---------- */
.secbill{border-radius:16px;overflow:hidden;border:1.5px solid var(--line);background:#fff;box-shadow:var(--sh)}
.secbill .sbh{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:12px 16px;color:#fff}
.secbill.hotel .sbh{background:linear-gradient(110deg,#e4501f,#ffa043)}
.secbill.bar .sbh{background:linear-gradient(110deg,#5a2fc0,#a47cf3)}
.sbh h3{margin:0;font-size:19px;margin-right:auto}
.sbh .btn{background:#fff;color:#2b1d14;padding:8px 14px;font-size:15px}
.secbill .sbb{padding:6px 14px 14px}
.sbtot{display:flex;justify-content:space-between;align-items:center;font-size:20px;font-weight:800;border-top:2px solid var(--line);padding-top:8px;margin-top:6px}
.secbill.hotel .sbtot b{color:#c2410c}.secbill.bar .sbtot b{color:var(--bar)}
.sbmini{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;color:var(--mut);margin:8px 0 2px}
.sbscroll{max-height:340px;overflow:auto}
.seg2{display:inline-flex;background:#f4ebdd;border-radius:12px;padding:3px}
.seg2 button{border:0;background:transparent;padding:6px 12px;border-radius:9px;font-weight:700;color:var(--mut)}
.seg2 button.on{background:#fff;color:var(--ink);box-shadow:0 1px 4px rgba(0,0,0,.12)}
.sbadge{display:inline-block;font-size:11px;font-weight:800;padding:2px 8px;border-radius:999px;color:#fff}
.sbadge.hotel{background:#e4701f}.sbadge.bar{background:var(--bar)}

/* ---------- reports ---------- */
.rep{display:grid;gap:16px}
.ph{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.ph h2{margin:0;color:var(--mar);font-size:21px;margin-right:auto}
.ph input,.ph select{padding:8px 10px;border:1.5px solid var(--line);border-radius:10px;background:#fffdf9}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.stat{border-radius:14px;padding:14px 16px;color:#fff;position:relative;overflow:hidden}
.stat span{font-size:14px;opacity:.9;font-weight:600}
.stat b{display:block;font-size:28px;line-height:1.2;margin-top:4px}
.stat:after{content:"";position:absolute;right:-20px;top:-20px;width:90px;height:90px;border-radius:50%;background:rgba(255,255,255,.12)}
.s1{background:linear-gradient(120deg,var(--mar3),var(--mar2))}
.s2{background:linear-gradient(120deg,#c2410c,#ffa043)}
.s3{background:linear-gradient(120deg,#4c22b0,#a47cf3)}
.s4{background:linear-gradient(120deg,#0a5f8c,#26a6df)}
table.tbl{width:100%;border-collapse:collapse;margin-top:12px}
.tbl th{text-align:left;font-size:13px;color:var(--mut);font-weight:700;padding:8px;border-bottom:2px solid var(--line);background:#fbf5ea}
.tbl td{padding:8px;border-bottom:1px solid #f3eadc;vertical-align:middle}
.tbl tr:hover td{background:#fffaf2}
.tbl .r{text-align:right}
.mbar{height:10px;border-radius:6px;background:linear-gradient(90deg,var(--sa),var(--mar2));min-width:3px}
.pbadge{font-size:12px;font-weight:700;padding:2px 9px;border-radius:999px}
.pbadge.cash{background:#e9f6ec;color:var(--cash)}
.pbadge.upi{background:#e3f3fb;color:var(--upi)}
.twocol{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.tblwrap{overflow-x:auto}

/* ---------- admin ---------- */
.login{max-width:380px;margin:40px auto;text-align:center;display:flex;flex-direction:column;gap:12px}
.login input{padding:12px;border:1.5px solid var(--line);border-radius:12px;font-size:20px;text-align:center;letter-spacing:6px}
.atabs{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.atabs button{border:1.5px solid var(--line);background:#fff;padding:9px 18px;border-radius:12px;font-weight:700;color:var(--mar)}
.atabs button.on{background:var(--mar);color:#fff;border-color:var(--mar)}
.atabs .ghost{margin-left:auto}
.tbl input.ci{width:100%;padding:6px 8px;border:1.5px solid var(--line);border-radius:8px}
.switch{position:relative;width:42px;height:24px;display:inline-block}
.switch input{opacity:0;width:0;height:0}
.switch span{position:absolute;inset:0;background:#d8cbbb;border-radius:999px;transition:.2s;cursor:pointer}
.switch span:before{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}
.switch input:checked+span{background:var(--veg)}
.switch input:checked+span:before{transform:translateX(18px)}
.icon{border:0;background:transparent;padding:4px 8px;border-radius:8px;font-weight:700;color:var(--mar)}
.icon:hover{background:#f4ebdd}
.form{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.form label{display:flex;flex-direction:column;font-size:13px;font-weight:600;color:var(--mut);gap:3px}
.form input,.form select,.form textarea{padding:9px 10px;border:1.5px solid var(--line);border-radius:10px;font-size:15px;color:var(--ink);background:#fffdf9;font-family:inherit}
.form .full{grid-column:1/-1}
.chk{flex-direction:row!important;align-items:center;gap:8px!important}
.vrow{display:grid;grid-template-columns:1fr 1fr 110px 36px;gap:6px;margin-bottom:6px}
.vrow input{padding:8px;border:1.5px solid var(--line);border-radius:9px;min-width:0}
.presets{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.presets button{border:1.5px dashed var(--sa);background:#fff8ec;border-radius:9px;padding:4px 10px;font-weight:600;color:#a4520a}

/* ---------- modal & toast ---------- */
#modal{position:fixed;inset:0;background:rgba(40,15,10,.45);display:none;align-items:center;justify-content:center;z-index:50;padding:14px}
#modal.show{display:flex}
.mbox{background:#fff;border-radius:18px;max-width:640px;width:100%;max-height:92vh;overflow:auto;padding:18px 20px;box-shadow:0 20px 60px rgba(0,0,0,.3);border-top:5px solid var(--sa)}
.mbox h3{margin:0 0 12px;color:var(--mar);font-size:21px}
.mbox h4{margin:14px 0 6px;color:var(--mar)}
.mact{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}
#toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(30px);background:#21130b;color:#fff;padding:11px 20px;border-radius:12px;font-weight:600;opacity:0;transition:.25s;z-index:60;pointer-events:none;max-width:90vw;text-align:center}
#toast.show{opacity:1;transform:translateX(-50%)}
#toast.err{background:var(--nv)}

/* ---------- responsive ---------- */
@media (max-width:1100px){ .billing{grid-template-columns:minmax(0,1fr) 360px} .stats{grid-template-columns:repeat(2,1fr)} }
@media (max-width:860px){
  header.top{padding:8px 12px;gap:8px}
  .hname{font-size:20px}
  nav{order:3;width:100%;margin:0;display:grid;grid-template-columns:1fr 1fr;gap:6px}
  nav button{padding:7px 8px;font-size:14px}
  .hright{margin-left:auto}
  .daybox{padding:3px 10px}.daybox b{font-size:16px}
  main{padding:10px}
  .billing{grid-template-columns:minmax(0,1fr)}
  .grid-wrap{max-height:none}
  .cart-pane{position:static;height:auto;min-height:0;overflow:visible}
  .cart-pane>.lines{max-height:none}
  .tstats{grid-template-columns:1fr 1fr 1fr}
  .grid{grid-template-columns:repeat(auto-fill,minmax(145px,1fr))}
  .twocol,.form,.dl{grid-template-columns:1fr}
  .fab{display:flex;position:fixed;right:14px;bottom:14px;z-index:30;border:0;border-radius:999px;padding:12px 18px;font-weight:800;font-size:16px;background:var(--mar);color:#fff;box-shadow:var(--sh2);gap:8px;align-items:center}
  .fab.hide{display:none}
  .vrow{grid-template-columns:1fr 1fr 80px 32px}
}

/* ---------- print (receipt) ---------- */
#printArea{display:none}
.rcpt{font-family:'Mukta','Noto Sans Devanagari',Arial,sans-serif;color:#000;font-size:12px;line-height:1.3;margin:0 auto}
.rcpt .rh{text-align:center;font-size:19px;font-weight:800}
.rcpt .rt{text-align:center;font-size:11px}
.rcpt .rc{text-align:center;font-size:11px}
.rcpt .rl{border-top:1px dashed #000;margin:5px 0}
.rcpt .rm{display:flex;justify-content:space-between;gap:6px}
.rcpt table{width:100%;border-collapse:collapse}
.rcpt th{font-size:11px;text-align:left;border-bottom:1px solid #000;padding:2px 0}
.rcpt td{padding:2px 0;vertical-align:top}
.rcpt .c{text-align:center}.rcpt .r{text-align:right}
.rcpt td span{font-size:10px}
.rcpt .rtot{display:flex;justify-content:space-between;font-size:16px;font-weight:800;border-top:1px solid #000;border-bottom:1px solid #000;padding:3px 0;margin-top:3px}
.rcpt .rf{text-align:center;font-weight:700;margin-top:4px}
.rcpt .rs{text-align:center;font-size:14px;font-weight:800;border:1px solid #000;border-radius:4px;padding:1px 0;margin:4px 0}
.rcpt+.rcpt{page-break-before:always;break-before:page}
@media print{
  body{background:#fff!important}
  body>*:not(#printArea){display:none!important}
  #printArea{display:block!important}
}
</style>
<style id="pageStyle">@page{size:80mm auto;margin:2mm}.rcpt{width:76mm}</style>
</head>
<body>
<header class="top">
  <div class="brand">
    <div class="logo">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#ffe2bf" stroke-width="2" stroke-linecap="round"><path d="M4 4l16 16"/><path d="M20 4L4 20"/><path d="M15 3c2.5 1 4.5 3 5.5 5.5"/><circle cx="6" cy="5.5" r="2.2"/></svg>
    </div>
    <div><div class="hname" id="hName"></div><div class="htag" id="hTag"></div></div>
  </div>
  <nav id="nav"></nav>
  <div class="hright">
    <div class="daybox" id="dayName"></div>
    <button class="langbtn" id="langBtn" onclick="toggleLang()"></button>
  </div>
</header>
<main id="view"></main>
<button class="fab hide" id="fab" onclick="document.querySelector('.cart-pane').scrollIntoView({behavior:'smooth'})"></button>
<div id="printArea"></div>
<div id="modal" onclick="if(event.target===this)closeModal()"><div class="mbox" id="mbox"></div></div>
<div id="toast"></div>

<script>
/* =================== TRANSLATIONS =================== */
const T={
mr:{billing:'बिलिंग',reports:'उत्पन्न अहवाल',bills:'बिल यादी',admin:'ॲडमिन',all:'सर्व',veg:'व्हेज',nonveg:'नॉन-व्हेज',
search:'पदार्थ शोधा...',allCats:'सर्व विभाग',cart:'चालू बिल',empty:'बिलात अजून काही नाही.<br>मेनूमधून पदार्थ निवडा.',
qty:'नग',price:'दर',amount:'रक्कम',subtotal:'एकूण',discount:'सूट (₹)',total:'एकूण देय',payment:'पेमेंट',cash:'रोख',upi:'UPI / ऑनलाइन',
table:'टेबल नं.',customer:'ग्राहकाचे नाव',datetime:'दिनांक व वेळ',now:'आत्ता',autoOn:'ऑटो',saveprint:'सेव्ह व प्रिंट',save:'सेव्ह',
clear:'रद्द',billno:'बिल क्र.',date:'दिनांक',time:'वेळ',item:'पदार्थ',items:'पदार्थ',todaySales:'आजचे उत्पन्न',
daily:'दैनिक उत्पन्न',monthly:'मासिक उत्पन्न',revenue:'एकूण उत्पन्न',billcount:'एकूण बिले',topitems:'सर्वाधिक विक्री झालेले पदार्थ',
nodata:'या कालावधीत कोणतीही माहिती नाही',exportcsv:'⬇ एक्सेल (CSV)',reprint:'🖨 प्रिंट',delete:'हटवा',edit:'बदला',cancel:'रद्द',
saveBtn:'सेव्ह करा',login:'लॉगिन',logout:'लॉगआउट',pin:'ॲडमिन पिन',pinHint:'डिफॉल्ट पिन: 1234 — सेटिंग्जमध्ये बदला',
wrongpin:'चुकीचा पिन',menuitems:'मेनू पदार्थ',categories:'विभाग',settings:'सेटिंग्ज',additem:'+ नवीन पदार्थ',addcat:'+ नवीन विभाग',
name_mr:'नाव (मराठी)',name_en:'नाव (English)',type:'प्रकार',sort:'क्रम',category:'विभाग',variants:'साईज व दर',addvariant:'+ साईज जोडा',
label_mr:'साईज (मराठी)',label_en:'साईज (English)',active:'चालू',saved:'सेव्ह झाले ✓',deleted:'हटवले',confirmDel:'नक्की हटवायचे?',
confirmCatDel:'या विभागातील सर्व पदार्थही हटवले जातील. नक्की हटवायचे?',hotel_mr:'हॉटेलचे नाव (मराठी)',hotel_en:'हॉटेलचे नाव (English)',
tag_mr:'टॅगलाइन (मराठी)',tag_en:'टॅगलाइन (English)',addr_mr:'पत्ता (मराठी)',addr_en:'पत्ता (English)',phone:'फोन नं.',gstin:'GSTIN (असल्यास)',
footer_mr:'बिलाखालील संदेश (मराठी)',footer_en:'बिलाखालील संदेश (English)',paper:'प्रिंटर पेपर साईज',newpin:'नवीन पिन (बदलायचा असल्यास)',
billSaved:'बिल सेव्ह झाले',addSomething:'आधी बिलात पदार्थ जोडा',single:'एकच दर',hf:'हाफ / फुल',phf:'प्लेट / हाफ / फुल',sb:'छोटी / मोठी',
actions:'कृती',noItems:'पदार्थ सापडले नाहीत',nameRequired:'नाव आवश्यक आहे',langBtn:'English',a4:'A4 पेपर',confirmClear:'चालू बिल रद्द करायचे?',
printTip:'टीप: प्रिंट विंडोमध्ये तुमचा थर्मल प्रिंटर निवडा. प्रत्येक वेळी विंडो टाळण्यासाठी Chrome "--kiosk-printing" ने उघडा.',
day:'दिवस',plate:'प्लेट',phoneShort:'फोन',inactive:'बंद',contact:'संपर्क',grand:'एकूण देय रक्कम',signIn:'ॲडमिन लॉगिन',
itemsN:'पदार्थ',viewBills:'बिले पहा',settingsSaved:'सेटिंग्ज सेव्ह झाल्या',pinChanged:'पिन बदलला',
tables:'टेबल्स',running:'चालू टेबल्स',runningTables:'चालू टेबल',runningAmt:'चालू बिलांची रक्कम',freeTables:'रिकामे टेबल',tableWord:'टेबल',free:'रिकामा',
noRunning:'सध्या कोणताही टेबल चालू नाही. खालून टेबल निवडा.',sec_hotel:'हॉटेल',sec_bar:'बियर बार',backTables:'← टेबल्स',openOther:'दुसरा टेबल उघडा',
billPrint:'बिल करा',clearTable:'टेबल रिकामा करा',confirmClearTable:'या टेबलवरील सर्व ऑर्डर रद्द करायची?',min:'मि.',hr:'तास',
menuEmptyBar:'बार मेनू अजून रिकामा आहे.<br>ॲडमिनमध्ये पदार्थ व दर जोडा.',goAdmin:'ॲडमिनकडे जा',finalBill:'अंतिम बिल',
sepBills:'हॉटेल व बारची बिले वेगवेगळी तयार होतील.',dayBill:'आजचे एकत्रित बिल',printDay:'प्रिंट',viewDay:'हा दिवस पहा',
billTitle_hotel:'हॉटेल बिल',billTitle_bar:'बियर बार बिल',dayTitle_hotel:'हॉटेल - दैनिक एकत्रित बिल',dayTitle_bar:'बियर बार - दैनिक एकत्रित बिल',
table_count:'टेबल संख्या',sectionW:'सेक्शन',
cancelTable:'टेबल रद्द करा',confirmCancelTable:'हा टेबल रद्द करायचा? या टेबलवरील सर्व ऑर्डर हटवली जाईल.',tableCancelled:'टेबल रद्द केला',
download:'बिले डाउनलोड करा',yearly:'वार्षिक बिल',yearW:'वर्ष',monthToMonth:'महिना ते महिना',dlFrom:'पासून',dlTo:'पर्यंत',
dlBills:'सर्व बिले (Excel)',dlSummary:'महिनावार सारांश (Excel)',wrongYear:'योग्य वर्ष टाका',pickMonths:'दोन्ही महिने निवडा'},
en:{billing:'Billing',reports:'Revenue Reports',bills:'Bill History',admin:'Admin',all:'All',veg:'Veg',nonveg:'Non-Veg',
search:'Search items...',allCats:'All Categories',cart:'Current Bill',empty:'Bill is empty.<br>Tap items from the menu.',
qty:'Qty',price:'Rate',amount:'Amount',subtotal:'Subtotal',discount:'Discount (₹)',total:'Total Payable',payment:'Payment',cash:'Cash',upi:'UPI / Online',
table:'Table No.',customer:'Customer Name',datetime:'Date & Time',now:'Now',autoOn:'Auto',saveprint:'Save & Print',save:'Save',
clear:'Clear',billno:'Bill No.',date:'Date',time:'Time',item:'Item',items:'Items',todaySales:"Today's Sales",
daily:'Daily Revenue',monthly:'Monthly Revenue',revenue:'Total Revenue',billcount:'Total Bills',topitems:'Top Selling Items',
nodata:'No data for this period',exportcsv:'⬇ Excel (CSV)',reprint:'🖨 Print',delete:'Delete',edit:'Edit',cancel:'Cancel',
saveBtn:'Save',login:'Login',logout:'Logout',pin:'Admin PIN',pinHint:'Default PIN: 1234 — change it in Settings',
wrongpin:'Wrong PIN',menuitems:'Menu Items',categories:'Categories',settings:'Settings',additem:'+ New Item',addcat:'+ New Category',
name_mr:'Name (Marathi)',name_en:'Name (English)',type:'Type',sort:'Order',category:'Category',variants:'Sizes & Prices',addvariant:'+ Add Size',
label_mr:'Size (Marathi)',label_en:'Size (English)',active:'Active',saved:'Saved ✓',deleted:'Deleted',confirmDel:'Delete this?',
confirmCatDel:'All items in this category will also be deleted. Continue?',hotel_mr:'Hotel Name (Marathi)',hotel_en:'Hotel Name (English)',
tag_mr:'Tagline (Marathi)',tag_en:'Tagline (English)',addr_mr:'Address (Marathi)',addr_en:'Address (English)',phone:'Phone',gstin:'GSTIN (optional)',
footer_mr:'Bill Footer (Marathi)',footer_en:'Bill Footer (English)',paper:'Printer Paper Size',newpin:'New PIN (only if changing)',
billSaved:'Bill saved',addSomething:'Add items to the bill first',single:'Single price',hf:'Half / Full',phf:'Plate / Half / Full',sb:'Small / Big',
actions:'Actions',noItems:'No items found',nameRequired:'Name is required',langBtn:'मराठी',a4:'A4 paper',confirmClear:'Clear the current bill?',
printTip:'Tip: choose your thermal printer in the print window. To skip the window every time, start Chrome with "--kiosk-printing".',
day:'Day',plate:'Plate',phoneShort:'Ph',inactive:'Off',contact:'Contact',grand:'Grand Total',signIn:'Admin Login',
itemsN:'items',viewBills:'View bills',settingsSaved:'Settings saved',pinChanged:'PIN changed',
tables:'Tables',running:'Running Tables',runningTables:'Running Tables',runningAmt:'Running Bills Total',freeTables:'Free Tables',tableWord:'Table',free:'Free',
noRunning:'No table is running right now. Pick a table below.',sec_hotel:'Hotel',sec_bar:'Beer Bar',backTables:'← Tables',openOther:'Open another table',
billPrint:'Make Bill',clearTable:'Clear table',confirmClearTable:'Cancel the whole order on this table?',min:'min',hr:'hr',
menuEmptyBar:'Bar menu is empty.<br>Add items and prices in Admin.',goAdmin:'Go to Admin',finalBill:'Final Bill',
sepBills:'Separate bills will be made for Hotel and Bar.',dayBill:"Today's Combined Bill",printDay:'Print',viewDay:'View this day',
billTitle_hotel:'HOTEL BILL',billTitle_bar:'BEER BAR BILL',dayTitle_hotel:'HOTEL - DAY BILL',dayTitle_bar:'BEER BAR - DAY BILL',
table_count:'Number of tables',sectionW:'Section',
cancelTable:'Cancel Table',confirmCancelTable:'Cancel this table? The whole order on it will be removed.',tableCancelled:'Table cancelled',
download:'Download Bills',yearly:'Yearly bill',yearW:'Year',monthToMonth:'Month to month',dlFrom:'From',dlTo:'To',
dlBills:'All bills (Excel)',dlSummary:'Month-wise summary (Excel)',wrongYear:'Enter a valid year',pickMonths:'Pick both months'}
};
const DAYS={mr:['रविवार','सोमवार','मंगळवार','बुधवार','गुरुवार','शुक्रवार','शनिवार'],en:['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']};
const MONTHS={mr:['जानेवारी','फेब्रुवारी','मार्च','एप्रिल','मे','जून','जुलै','ऑगस्ट','सप्टेंबर','ऑक्टोबर','नोव्हेंबर','डिसेंबर'],
en:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']};

/* =================== STATE =================== */
let LANG='mr'; try{LANG=localStorage.getItem('ak_lang')||'mr'}catch(e){}
let PIN=''; try{PIN=sessionStorage.getItem('ak_pin')||''}catch(e){}
let MENU={categories:[],items:[]}, SETTINGS={};
let VIEW='tables', TABLE='', SEC='hotel', FILTER='all', CAT=0, Q='';
let ATAB='menuitems', ACAT=0, ASEC='all', AQ='', EDIT_VARS=[];
let BDATE='', BSEC='all', BILLS=[], SAVING=false, DAYREP=null;

/* =================== HELPERS =================== */
const $=id=>document.getElementById(id);
function t(k){return (T[LANG]&&T[LANG][k]!==undefined)?T[LANG][k]:(T.en[k]!==undefined?T.en[k]:k)}
const DEV='०१२३४५६७८९';
function n(x){x=String(x??'');return LANG==='mr'?x.replace(/[0-9]/g,d=>DEV[+d]):x}
function fmt(v){v=Number(v)||0;return v.toLocaleString('en-IN',{maximumFractionDigits:2})}
function money(v){return '₹'+n(fmt(v))}
function nm(o){return LANG==='mr'?(o.name_mr||o.name_en):(o.name_en||o.name_mr)}
function vl(v){return LANG==='mr'?(v.mr||v.en):(v.en||v.mr)}
function lv(l){return LANG==='mr'?(l.vmr||l.ven):(l.ven||l.vmr)}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function pad(x){return String(x).padStart(2,'0')}
function todayStr(d){d=d||new Date();return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())}
function monthStr(d){d=d||new Date();return d.getFullYear()+'-'+pad(d.getMonth()+1)}
function toLocalInput(d){return todayStr(d)+'T'+pad(d.getHours())+':'+pad(d.getMinutes())}
function parseDT(s){const m=/(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(s||'');return m?new Date(+m[1],m[2]-1,+m[3],+m[4],+m[5]):new Date()}
function fmtTime(d){let h=d.getHours(),ap=h>=12?(LANG==='mr'?'PM':'PM'):'AM';h=h%12||12;return n(h+':'+pad(d.getMinutes()))+' '+ap}
function fmtDate(d){return n(pad(d.getDate()))+' '+MONTHS[LANG][d.getMonth()]+' '+n(d.getFullYear())}
function fmtDT(d){return fmtDate(d)+', '+fmtTime(d)}
function fmtDay(s){const d=parseDT(s+' 00:00');return n(pad(d.getDate()))+' '+MONTHS[LANG][d.getMonth()]+' • '+DAYS[LANG][d.getDay()]}
function catName(id){const c=MENU.categories.find(c=>c.id===id);return c?nm(c):'-'}
function toast(msg,err){const el=$('toast');el.textContent=msg;el.className='show'+(err?' err':'');clearTimeout(el._t);el._t=setTimeout(()=>el.className='',2600)}
function openModal(html){$('mbox').innerHTML=html;$('modal').classList.add('show')}
function closeModal(){$('modal').classList.remove('show')}

async function api(path,method,body){
  const r=await fetch(path,{method:method||'GET',headers:{'Content-Type':'application/json','X-Admin-Pin':PIN},body:body?JSON.stringify(body):undefined});
  let j={};try{j=await r.json()}catch(e){}
  if(r.status===401&&PIN&&path!=='/api/login'){PIN='';try{sessionStorage.removeItem('ak_pin')}catch(e){}}
  if(!r.ok)throw new Error(j.error||('Error '+r.status));
  return j;
}
async function loadAll(){
  const [m,s]=await Promise.all([api('/api/menu'),api('/api/settings')]);
  MENU=m;SETTINGS=s;
}

/* =================== SHELL =================== */
const SECTIONS=['hotel','bar'];
function secIcon(s){return s==='bar'?'🍺':'🍽'}
function setHtml(el,h){if(el&&el._h!==h){el.innerHTML=h;el._h=h}}
function tickDay(){
  const d=new Date();
  setHtml($('dayName'),'<b>'+DAYS[LANG][d.getDay()]+'</b><small>'+fmtDate(d)+'</small>');
}
function render(){
  document.documentElement.lang=LANG;
  document.title=(SETTINGS['hotel_'+LANG]||'Hotel Akshara')+' - '+t('billing');
  $('hName').textContent=SETTINGS['hotel_'+LANG]||SETTINGS.hotel_mr||'';
  $('hTag').textContent=SETTINGS['tag_'+LANG]||'';
  $('langBtn').textContent='🌐 '+t('langBtn');
  $('nav').innerHTML=['tables','reports','bills','admin'].map(v=>{
    const ic={tables:'🍽',reports:'📊',bills:'📋',admin:'⚙️'}[v];
    const on=VIEW===v||(v==='tables'&&VIEW==='order');
    return `<button class="${on?'on':''}" onclick="go('${v}')">${ic} ${t(v)}${v==='tables'?'<span class="nbadge" id="navCnt"></span>':''}</button>`}).join('');
  $('fab').classList.add('hide');
  if(VIEW==='tables')viewTables();
  else if(VIEW==='order')viewOrder();
  else if(VIEW==='reports')viewReports();
  else if(VIEW==='bills')viewBills();
  else viewAdmin();
  $('dayName')._h=null;tickDay();updateNavBadge();
}
function go(v){VIEW=v;render();window.scrollTo(0,0)}
function toggleLang(){LANG=LANG==='mr'?'en':'mr';try{localStorage.setItem('ak_lang',LANG)}catch(e){};render()}

/* =================== OPEN TABLE ORDERS =================== */
let ORD={}, ORDSIG='';
const DIRTY=new Set();let FLUSHING=null;
function nowStr(){const d=new Date();return todayStr(d)+' '+pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds())}
function curOrder(){return ORD[TABLE]||(ORD[TABLE]={table_no:TABLE,customer:'',items:[],created_at:nowStr()})}
function osum(o,s){return o.items.reduce((a,l)=>a+((!s||l.section===s)?l.price*l.qty:0),0)}
function ocount(o){return o.items.reduce((a,l)=>a+l.qty,0)}
function runningOrders(){
  return Object.values(ORD).filter(o=>o.items.length)
    .sort((a,b)=>a.created_at<b.created_at?-1:a.created_at>b.created_at?1:(+a.table_no)-(+b.table_no));
}
function tableCount(){
  const mx=Math.max(0,...runningOrders().map(o=>+o.table_no||0));
  return Math.max(+SETTINGS.table_count||15,mx);
}
function elapsed(o){
  const m=Math.max(0,Math.floor((Date.now()-parseDT(o.created_at))/60000));
  return m<60?n(m)+' '+t('min'):n(Math.floor(m/60))+' '+t('hr')+' '+n(m%60)+' '+t('min');
}
function updateNavBadge(){const e=$('navCnt');if(e)e.textContent=runningOrders().length?n(runningOrders().length):''}
function persist(tn){DIRTY.add(tn);if(!FLUSHING)FLUSHING=flush()}
async function flush(){
  await 0;
  try{
    while(DIRTY.size){
      const tn=DIRTY.values().next().value;DIRTY.delete(tn);
      const o=ORD[tn];if(!o)continue;
      try{await api('/api/orders/'+encodeURIComponent(tn),'PUT',{customer:o.customer,items:o.items})}
      catch(e){toast(e.message,true)}
    }
  }finally{FLUSHING=null}
}
async function flushNow(){while(FLUSHING)await FLUSHING}
async function pollOrders(){
  if(FLUSHING||DIRTY.size)return;
  try{
    const list=await api('/api/orders');
    const sig=JSON.stringify(list.map(o=>[o.table_no,o.updated_at,o.total,o.count]));
    if(FLUSHING||DIRTY.size||sig===ORDSIG)return;
    ORDSIG=sig;
    const m={};list.forEach(o=>m[o.table_no]=o);
    if(VIEW==='order'&&ORD[TABLE])m[TABLE]=ORD[TABLE];   // never overwrite the table being edited
    ORD=m;refreshOrdUI();
  }catch(e){}
}
function refreshOrdUI(){
  updateNavBadge();
  if(VIEW==='tables')renderTablesBody();
  else if(VIEW==='order')renderStrip();
}

/* =================== TABLES (home) =================== */
function viewTables(){$('view').innerHTML='<div id="tablesBox"></div>';renderTablesBody()}
function renderTablesBody(){
  const box=$('tablesBox');if(!box)return;
  const run=runningOrders(),N=tableCount();
  const amt=run.reduce((s,o)=>s+osum(o),0);
  let h=`<div class="tstats">
    <div class="tstat ts1"><span>🔥 ${t('runningTables')}</span><b>${n(run.length)}</b></div>
    <div class="tstat ts2"><span>💰 ${t('runningAmt')}</span><b>${money(amt)}</b></div>
    <div class="tstat ts3"><span>✅ ${t('freeTables')}</span><b>${n(Math.max(0,N-run.length))}</b></div></div>
  <section class="panel runbox"><h3>🔥 ${t('running')}</h3>`+
  (run.length?`<div class="runlist">${run.map(o=>`<button class="chip" onclick="openTable('${esc(o.table_no)}')"><span class="cn">${n(esc(o.table_no))}</span><span>${money(osum(o))}<small>⏱ ${elapsed(o)} • ${n(ocount(o))} ${t('itemsN')}</small></span></button>`).join('')}</div>`
    :`<p class="muted" style="margin:0">${t('noRunning')}</p>`)+`</section><div class="tgrid">`;
  for(let i=1;i<=N;i++){
    const o=ORD[i]&&ORD[i].items.length?ORD[i]:null;
    if(o){const hs=osum(o,'hotel'),bs=osum(o,'bar');
      h+=`<button class="tcard on" onclick="openTable(${i})"><div><div class="tlab">${t('tableWord')}</div><div class="tno">${n(i)}</div></div>
        <div><div class="tamt">${money(osum(o))}</div><div class="trow">${hs?`<span class="tpill">🍽 ${money(hs)}</span>`:''}${bs?`<span class="tpill">🍺 ${money(bs)}</span>`:''}</div><div class="tmeta">⏱ ${elapsed(o)}</div></div></button>`;
    }else h+=`<button class="tcard free" onclick="openTable(${i})"><div><div class="tlab">${t('tableWord')}</div><div class="tno">${n(i)}</div></div><div class="tlab">✓ ${t('free')}</div></button>`;
  }
  setHtml(box,h+'</div>');
}
async function openTable(tn){
  tn=String(tn);
  if(!FLUSHING&&!DIRTY.size){
    try{const o=await api('/api/orders/'+encodeURIComponent(tn));ORD[tn]=o.items.length?o:{table_no:tn,customer:'',items:[],created_at:nowStr()}}catch(e){}
  }
  TABLE=tn;VIEW='order';Q='';render();window.scrollTo(0,0);
}

/* =================== ORDER SCREEN =================== */
function viewOrder(){
  const o=curOrder();
  $('view').innerHTML=`<div class="ohead">
    <button class="btn dark" onclick="go('tables')">${t('backTables')}</button>
    <div class="otitle">${t('tableWord')} <span>${n(esc(TABLE))}</span></div>
    <div class="strip" id="strip"></div>
    <button class="btn cancelT" onclick="cancelTable()">✕ ${t('cancelTable')}</button>
  </div>
  <div class="billing">
   <section class="panel menu sec-${SEC}" id="menuPanel">
     <div class="secsw" id="secSw"></div>
     <div class="toolbar"><div class="seg" id="typeSeg"></div>
       <input class="search" id="search" placeholder="🔍 ${esc(t('search'))}" value="${esc(Q)}" oninput="Q=this.value;renderGrid()"></div>
     <div class="cats" id="cats"></div>
     <div class="grid-wrap" id="grid"></div>
   </section>
   <aside class="panel cart-pane">
     <h3>🧾 ${t('cart')} <span class="badge" id="lineCount"></span></h3>
     <input class="cinput" id="cust" placeholder="${esc(t('customer'))}" value="${esc(o.customer)}" oninput="curOrder().customer=this.value" onchange="persist(TABLE)">
     <div class="lines" id="lines"></div>
     <div class="grand tr"><span>${t('total')}</span><b id="grand"></b></div>
     <div class="acts">
       <button class="btn pri" onclick="openCheckout()">🧾 ${t('billPrint')}</button></div>
   </aside></div>`;
  renderSecSw();renderTypeSeg();renderCats();renderGrid();renderCart();renderStrip();
}
function renderStrip(){
  const run=runningOrders();
  setHtml($('strip'),run.map(o=>`<button class="chip ${o.table_no===TABLE?'cur':''}" onclick="openTable('${esc(o.table_no)}')"><span class="cn">${n(esc(o.table_no))}</span><span>${money(osum(o))}</span></button>`).join(''));
}
function renderSecSw(){
  $('secSw').innerHTML=SECTIONS.map(s=>`<button class="${s} ${SEC===s?'on':''}" onclick="setSec('${s}')">${secIcon(s)} ${t('sec_'+s)}</button>`).join('');
  $('menuPanel').className='panel menu sec-'+SEC;
}
function setSec(s){SEC=s;CAT=0;FILTER='all';Q='';$('search').value='';renderSecSw();renderTypeSeg();renderCats();renderGrid()}
function activeItems(){return MENU.items.filter(i=>i.active&&i.section===SEC&&(SEC==='bar'||FILTER==='all'||i.type===FILTER))}
function renderTypeSeg(){
  const sg=$('typeSeg');
  if(SEC==='bar'){sg.style.display='none';return}
  sg.style.display='';
  sg.innerHTML=[['all',''],['veg','<span class="dot"></span>'],['nonveg','<span class="dot nonveg"></span>']]
   .map(([k,ic])=>`<button class="${FILTER===k?'on':''}" onclick="FILTER='${k}';CAT=0;renderTypeSeg();renderCats();renderGrid()">${ic}${t(k)}</button>`).join('');
}
function renderCats(){
  const items=activeItems();
  const cats=MENU.categories.filter(c=>c.section===SEC&&items.some(i=>i.category_id===c.id));
  if(CAT&&!cats.some(c=>c.id===CAT))CAT=0;
  $('cats').innerHTML=`<button class="${CAT===0?'on':''}" onclick="CAT=0;renderCats();renderGrid()">${t('allCats')}</button>`+
    cats.map(c=>`<button class="${CAT===c.id?'on':''}" onclick="CAT=${c.id};renderCats();renderGrid()">${esc(nm(c))}<small>${n(items.filter(i=>i.category_id===c.id).length)}</small></button>`).join('');
}
function renderGrid(){
  const q=Q.trim().toLowerCase();
  const all=activeItems();
  const items=all.filter(i=>(!CAT||i.category_id===CAT)&&(!q||(i.name_mr+' '+i.name_en).toLowerCase().includes(q)));
  if(!items.length){
    $('grid').innerHTML=`<div class="empty">${all.length?t('noItems'):(SEC==='bar'?t('menuEmptyBar'):t('noItems'))}${!all.length&&SEC==='bar'?`<br><button class="btn pri" onclick="go('admin')">⚙️ ${t('goAdmin')}</button>`:''}</div>`;return}
  const groups=MENU.categories.filter(c=>c.section===SEC).map(c=>({c,list:items.filter(i=>i.category_id===c.id)})).filter(g=>g.list.length);
  $('grid').innerHTML=groups.map(g=>`<div class="ghead">${esc(nm(g.c))}</div><div class="grid">${g.list.map(card).join('')}</div>`).join('');
}
function card(it){
  const single=it.variants.length===1;
  const head=`<div class="ctop">${it.section==='bar'?'':`<span class="dot ${it.type}"></span>`}<span class="iname">${esc(nm(it))}</span></div>`;
  if(single){const v=it.variants[0];
    return `<div class="card click" onclick="addItem(${it.id},0)">${head}<div class="price">${money(v.p)}${vl(v)?` <span class="badge">${esc(vl(v))}</span>`:''}</div></div>`}
  return `<div class="card">${head}<div class="vars">${it.variants.map((v,i)=>`<button onclick="addItem(${it.id},${i})"><small>${esc(vl(v))}</small><b>${money(v.p)}</b></button>`).join('')}</div></div>`;
}
function afterChange(k){renderCart(k);persist(TABLE);renderStrip();updateNavBadge()}
function addItem(id,vi){
  const it=MENU.items.find(x=>x.id===id);if(!it)return;const v=it.variants[vi],o=curOrder();
  let k=o.items.findIndex(l=>l.item_id===id&&(l.vmr||'')===(v.mr||'')&&(l.ven||'')===(v.en||'')&&l.price===Number(v.p));
  if(k>=0)o.items[k].qty++;
  else{o.items.push({item_id:id,section:it.section,name_mr:it.name_mr,name_en:it.name_en,vmr:v.mr||'',ven:v.en||'',price:Number(v.p),qty:1});k=o.items.length-1}
  afterChange(k);
}
function chQty(i,d){const o=curOrder(),l=o.items[i];l.qty+=d;if(l.qty<=0)o.items.splice(i,1);afterChange(d>0?i:-1)}
function rmLine(i){curOrder().items.splice(i,1);afterChange(-1)}
function chPrice(i,v){
  const l=curOrder().items[i];l.price=Math.max(0,Number(v)||0);
  const el=$('lt'+i);if(el)el.textContent=money(l.price*l.qty);
  renderTotals();persist(TABLE);renderStrip();
}
function lineHtml(l,i){
  return `<div class="line" id="ln${i}">
    <div class="lname">${esc(nm(l))}${lv(l)?`<small>(${esc(lv(l))})</small>`:''}</div>
    <div class="lctrl">
      <button class="qbtn" onclick="chQty(${i},-1)">−</button><span class="qty">${n(l.qty)}</span><button class="qbtn" onclick="chQty(${i},1)">+</button>
      <span class="muted">× ₹</span><input type="number" min="0" class="pin" value="${l.price}" oninput="chPrice(${i},this.value)" title="${esc(t('price'))}">
      <span class="ltot" id="lt${i}">${money(l.price*l.qty)}</span>
      <button class="x" onclick="rmLine(${i})" title="${esc(t('delete'))}">✕</button>
    </div></div>`;
}
function renderCart(fl){
  const box=$('lines');if(!box)return;const o=curOrder();
  if(!o.items.length){
    box.innerHTML=`<div class="empty"><svg width="54" height="54" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 2h12v20l-3-2-3 2-3-2-3 2z"/><path d="M9 7h6M9 11h6M9 15h4"/></svg>${t('empty')}</div>`;
  }else{
    box.innerHTML=SECTIONS.map(s=>{
      const idx=o.items.map((l,i)=>i).filter(i=>o.items[i].section===s);
      if(!idx.length)return '';
      return `<div class="lsec ${s}"><span>${secIcon(s)} ${t('sec_'+s)}</span><b id="ls_${s}"></b></div>`+idx.map(i=>lineHtml(o.items[i],i)).join('');
    }).join('');
  }
  renderTotals();
  const el=fl>=0&&$('ln'+fl);
  if(el){el.classList.add('flash');
    const top=el.offsetTop;
    if(top<box.scrollTop)box.scrollTop=top;
    else if(top+el.offsetHeight>box.scrollTop+box.clientHeight)box.scrollTop=top+el.offsetHeight-box.clientHeight}
}
function renderTotals(){
  const o=curOrder(),tot=osum(o),cnt=ocount(o);
  SECTIONS.forEach(s=>{const e=$('ls_'+s);if(e)e.textContent=money(osum(o,s))});
  if($('grand'))$('grand').textContent=money(tot);
  if($('lineCount'))$('lineCount').textContent=cnt?n(cnt)+' '+t('itemsN'):'';
  const f=$('fab');f.textContent='🧾 '+n(cnt)+' • '+money(tot);f.classList.toggle('hide',!cnt||VIEW!=='order');
}
function cancelTable(){
  const o=curOrder();
  if(o.items.length&&!confirm(t('confirmCancelTable')))return;
  o.items=[];o.customer='';persist(TABLE);
  if(o.items.length===0)toast(t('tableCancelled'));
  VIEW='tables';render();
}

/* =================== CHECKOUT =================== */
let CO={disc:{hotel:0,bar:0}};
async function openCheckout(){
  const o=curOrder();
  if(!o.items.length)return toast(t('addSomething'),true);
  await flushNow();
  CO={disc:{hotel:0,bar:0}};
  const secs=SECTIONS.filter(s=>o.items.some(l=>l.section===s));
  openModal(`<h3>🧾 ${t('finalBill')} — ${t('tableWord')} ${n(esc(TABLE))}</h3>
   ${secs.length>1?`<div class="note">ℹ️ ${t('sepBills')}</div>`:''}
   ${secs.map(s=>`<div class="cosec"><div class="lsec ${s}"><span>${secIcon(s)} ${t('sec_'+s)}</span><b>${money(osum(o,s))}</b></div><div class="cob">
      ${o.items.filter(l=>l.section===s).map(l=>`<div class="corow sm"><span>${esc(nm(l))}${lv(l)?' ('+esc(lv(l))+')':''} × ${n(l.qty)}</span><span>${money(l.price*l.qty)}</span></div>`).join('')}
      <div class="corow" style="align-items:center;margin-top:6px"><span>${t('discount')}</span><input type="number" min="0" placeholder="0" oninput="coDisc('${s}',this.value)"></div>
      <div class="corow net"><span>${t('total')}</span><span id="cot_${s}"></span></div></div></div>`).join('')}
   <div class="grand tr"><span>${t('grand')}</span><b id="coGrand"></b></div>
   <div class="fld" style="margin-top:10px"><label>${t('datetime')}</label><input type="datetime-local" id="coTime" value="${toLocalInput(new Date())}"></div>
   <div class="mact"><button class="ghost" onclick="closeModal()">${t('cancel')}</button>
     <button class="btn pri" onclick="doCheckout()">🖨 ${t('saveprint')}</button></div>`);
  coTotals();
}
function coDisc(s,v){CO.disc[s]=Math.max(0,+v||0);coTotals()}
function coTotals(){
  const o=curOrder();let g=0;
  SECTIONS.forEach(s=>{const sub=osum(o,s);if(!sub&&!o.items.some(l=>l.section===s))return;
    const net=sub-Math.min(CO.disc[s]||0,sub);g+=net;const e=$('cot_'+s);if(e)e.textContent=money(net)});
  $('coGrand').textContent=money(g);
}
async function doCheckout(){
  if(SAVING)return;SAVING=true;
  try{
    await flushNow();
    const r=await api('/api/orders/'+encodeURIComponent(TABLE)+'/checkout','POST',
      {discounts:CO.disc,created_at:($('coTime').value||'').replace('T',' ')});
    delete ORD[TABLE];closeModal();
    toast(t('billSaved')+' — '+r.bills.map(b=>t('sec_'+b.section)+' #'+n(b.id)+' '+money(b.total)).join(' • '));
    printBills(r.bills);
    VIEW='tables';render();
  }catch(e){toast(e.message,true)}
  finally{SAVING=false}
}

/* =================== PRINT =================== */
function setPageStyle(){
  const p=SETTINGS.paper||'80';
  $('pageStyle').textContent=p==='a4'?'@page{size:A4;margin:12mm}.rcpt{width:90mm;font-size:13px}':
    `@page{size:${p}mm auto;margin:2mm}.rcpt{width:${p-4}mm}`+(p==='58'?'.rcpt{font-size:11px}.rcpt .rh{font-size:16px}':'');
}
function printReceipts(list){
  $('printArea').innerHTML=list.join('');
  setPageStyle();
  setTimeout(()=>window.print(),200);
}
function rcptTop(title){
  const g=k=>SETTINGS[k+'_'+LANG]||SETTINGS[k+'_mr']||SETTINGS[k+'_en']||'';
  return `<div class="rh">${esc(g('hotel'))}</div>
    ${g('tag')?`<div class="rt">${esc(g('tag'))}</div>`:''}
    ${g('addr')?`<div class="rc">${esc(g('addr'))}</div>`:''}
    ${SETTINGS.phone?`<div class="rc">${t('phoneShort')}: ${n(esc(SETTINGS.phone))}</div>`:''}
    ${SETTINGS.gstin?`<div class="rc">GSTIN: ${esc(SETTINGS.gstin)}</div>`:''}
    <div class="rs">${esc(title)}</div>`;
}
function rcptFoot(){return `<div class="rl"></div><div class="rf">${esc(SETTINGS['footer_'+LANG]||SETTINGS.footer_mr||SETTINGS.footer_en||'')}</div>`}
function billReceipt(b){
  const d=parseDT(b.created_at);
  const rows=b.items.map(l=>`<tr><td>${esc(nm(l))}${lv(l)?` <span>(${esc(lv(l))})</span>`:''}</td><td class="c">${n(l.qty)}</td><td class="r">${n(fmt(l.price))}</td><td class="r">${n(fmt(l.price*l.qty))}</td></tr>`).join('');
  return `<div class="rcpt">${rcptTop(t('billTitle_'+b.section))}
    <div class="rl"></div>
    <div class="rm"><span>${t('billno')}: <b>${n(b.id)}</b></span><span>${t('table')}: <b>${n(esc(b.table_no||'-'))}</b></span></div>
    <div class="rm"><span>${t('date')}: ${fmtDate(d)}</span><span>${fmtTime(d)}</span></div>
    ${b.customer?`<div class="rm"><span>${t('customer')}: ${esc(b.customer)}</span></div>`:''}
    <div class="rl"></div>
    <table><thead><tr><th>${t('item')}</th><th class="c">${t('qty')}</th><th class="r">${t('price')}</th><th class="r">${t('amount')}</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="rl"></div>
    <div class="rm"><span>${t('subtotal')}</span><span>${money(b.subtotal)}</span></div>
    ${b.discount>0?`<div class="rm"><span>${t('discount')}</span><span>- ${money(b.discount)}</span></div>`:''}
    <div class="rtot"><span>${t('grand')}</span><span>${money(b.total)}</span></div>
    ${rcptFoot()}</div>`;
}
function printBills(list){printReceipts(list.map(billReceipt))}
function dayReceipt(s,x,date){
  const d=parseDT(date+' 00:00');
  const rows=x.items.map(l=>`<tr><td>${esc(nm(l))}${lv(l)?` <span>(${esc(lv(l))})</span>`:''}</td><td class="c">${n(l.qty)}</td><td class="r">${n(fmt(l.price))}</td><td class="r">${n(fmt(l.amount))}</td></tr>`).join('');
  return `<div class="rcpt">${rcptTop(t('dayTitle_'+s))}
    <div class="rl"></div>
    <div class="rm"><span>${t('date')}: <b>${fmtDate(d)}</b></span><span>${DAYS[LANG][d.getDay()]}</span></div>
    <div class="rm"><span>${t('billcount')}: <b>${n(x.count)}</b></span></div>
    <div class="rl"></div>
    <table><thead><tr><th>${t('item')}</th><th class="c">${t('qty')}</th><th class="r">${t('price')}</th><th class="r">${t('amount')}</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="rl"></div>
    <div class="rm"><span>${t('subtotal')}</span><span>${money(x.subtotal)}</span></div>
    ${x.discount>0?`<div class="rm"><span>${t('discount')}</span><span>- ${money(x.discount)}</span></div>`:''}
    <div class="rtot"><span>${t('grand')}</span><span>${money(x.total)}</span></div>
    ${rcptFoot()}</div>`;
}
function printDay(s){if(DAYREP)printReceipts([dayReceipt(s,DAYREP.sections[s],DAYDATE)])}

/* =================== REPORTS =================== */
let DAYDATE='';
function statCards(d){return `<div class="stats">
  <div class="stat s1"><span>💰 ${t('revenue')}</span><b>${money(d.total)}</b></div>
  <div class="stat s2"><span>🍽 ${t('sec_hotel')}</span><b>${money(d.hotel)}</b></div>
  <div class="stat s3"><span>🍺 ${t('sec_bar')}</span><b>${money(d.bar)}</b></div>
  <div class="stat s4"><span>🧾 ${t('billcount')}</span><b>${n(d.count)}</b></div></div>`}
function viewReports(){
  $('view').innerHTML=`<div class="rep">
   <section class="panel"><div class="ph"><h2>📅 ${t('daily')}</h2><input type="date" id="rDate" value="${DAYDATE||todayStr()}" onchange="loadDay()"></div><div id="dayBox"></div></section>
   <section class="panel"><div class="ph"><h2>🗓 ${t('monthly')}</h2><input type="month" id="rMonth" value="${monthStr()}" onchange="loadMonth()"></div><div id="monthBox"></div></section>
   <section class="panel"><div class="ph"><h2>⬇ ${t('download')}</h2>
     <select id="dlSec"><option value="all">${t('all')}</option><option value="hotel">🍽 ${t('sec_hotel')}</option><option value="bar">🍺 ${t('sec_bar')}</option></select></div>
     <div class="dl">
      <div class="dlbox"><h4>📆 ${t('yearly')}</h4>
        <div class="dlrow"><label>${t('yearW')}<input type="number" id="dlYear" min="2000" max="2100" value="${new Date().getFullYear()}"></label></div>
        <div class="dlbtns"><button class="btn pri" onclick="dlYear('bills')">⬇ ${t('dlBills')}</button><button class="btn dark" onclick="dlYear('summary')">⬇ ${t('dlSummary')}</button></div></div>
      <div class="dlbox"><h4>🗓 ${t('monthToMonth')}</h4>
        <div class="dlrow"><label>${t('dlFrom')}<input type="month" id="dlFrom" value="${monthStr()}"></label><label>${t('dlTo')}<input type="month" id="dlTo" value="${monthStr()}"></label></div>
        <div class="dlbtns"><button class="btn pri" onclick="dlRange('bills')">⬇ ${t('dlBills')}</button><button class="btn dark" onclick="dlRange('summary')">⬇ ${t('dlSummary')}</button></div></div>
     </div></section></div>`;
  loadDay();loadMonth();
}
function secBillCard(s,x){
  const body=x.count?`<div class="sbmini"><span>🧾 ${t('billcount')}: <b>${n(x.count)}</b></span></div>
    <div class="sbscroll"><table class="tbl"><thead><tr><th>${t('item')}</th><th class="r">${t('qty')}</th><th class="r">${t('price')}</th><th class="r">${t('amount')}</th></tr></thead><tbody>${
      x.items.map(l=>`<tr><td>${esc(nm(l))}${lv(l)?` <span class="badge">${esc(lv(l))}</span>`:''}</td><td class="r">${n(l.qty)}</td><td class="r">${n(fmt(l.price))}</td><td class="r"><b>${money(l.amount)}</b></td></tr>`).join('')}</tbody></table></div>
    ${x.discount>0?`<div class="tr muted" style="margin-top:6px"><span>${t('discount')}</span><span>- ${money(x.discount)}</span></div>`:''}
    <div class="sbtot"><span>${t('grand')}</span><b>${money(x.total)}</b></div>`
    :`<p class="muted" style="text-align:center;padding:18px 0">${t('nodata')}</p>`;
  return `<div class="secbill ${s}"><div class="sbh"><h3>${secIcon(s)} ${t('sec_'+s)} — ${t('dayBill')}</h3>
    <button class="btn" ${x.count?'':'disabled'} onclick="printDay('${s}')">🖨 ${t('printDay')}</button></div><div class="sbb">${body}</div></div>`;
}
async function loadDay(){
  DAYDATE=$('rDate').value;
  try{const d=await api('/api/report/day?date='+DAYDATE);DAYREP=d;
    $('dayBox').innerHTML=statCards(d)+`<div class="twocol" style="margin-top:14px">${SECTIONS.map(s=>secBillCard(s,d.sections[s])).join('')}</div>`;
  }catch(e){toast(e.message,true)}
}
function dlGo(from,to,kind){
  const sc=$('dlSec').value;
  const a=document.createElement('a');
  a.href='/api/export?from='+from+'&to='+to+'&kind='+kind+(sc!=='all'?'&section='+sc:'');
  document.body.appendChild(a);a.click();a.remove();
}
function dlYear(kind){const y=+$('dlYear').value;if(!(y>=2000&&y<=2100))return toast(t('wrongYear'),true);dlGo(y+'-01',y+'-12',kind)}
function dlRange(kind){const f=$('dlFrom').value,to=$('dlTo').value;if(!f||!to)return toast(t('pickMonths'),true);dlGo(f,to,kind)}
async function loadMonth(){
  const m=$('rMonth').value;
  try{const d=await api('/api/report/month?month='+m);const mx=Math.max(1,...d.days.map(x=>x.total));
    $('monthBox').innerHTML=statCards(d)+(d.days.length?`<div class="tblwrap"><table class="tbl"><thead><tr><th>${t('date')}</th><th class="r">${t('billcount')}</th><th class="r">🍽 ${t('sec_hotel')}</th><th class="r">🍺 ${t('sec_bar')}</th><th class="r">${t('revenue')}</th><th style="width:22%"></th></tr></thead><tbody>${
      d.days.map(x=>`<tr style="cursor:pointer" onclick="DAYDATE='${x.date}';go('reports')" title="${esc(t('viewDay'))}"><td>${fmtDay(x.date)}</td><td class="r">${n(x.count)}</td><td class="r">${money(x.hotel)}</td><td class="r">${money(x.bar)}</td><td class="r"><b>${money(x.total)}</b></td><td><div class="mbar" style="width:${(x.total/mx*100).toFixed(1)}%"></div></td></tr>`).join('')}</tbody></table></div>`:`<p class="muted" style="text-align:center">${t('nodata')}</p>`);
  }catch(e){toast(e.message,true)}
}

/* =================== BILL HISTORY =================== */
function viewBills(){
  $('view').innerHTML=`<section class="panel"><div class="ph"><h2>📋 ${t('bills')}</h2>
    <div class="seg2">${['all','hotel','bar'].map(k=>`<button class="${BSEC===k?'on':''}" onclick="BSEC='${k}';viewBills()">${k==='all'?t('all'):secIcon(k)+' '+t('sec_'+k)}</button>`).join('')}</div>
    <input type="date" id="bDate" value="${BDATE||todayStr()}" onchange="BDATE=this.value;loadBills()"></div><div id="billsBox"></div></section>`;
  loadBills();
}
async function loadBills(){
  try{BILLS=await api('/api/bills?date='+$('bDate').value);
    const list=BILLS.filter(b=>BSEC==='all'||b.section===BSEC);
    if(!list.length){$('billsBox').innerHTML=`<p class="muted" style="text-align:center;padding:20px">${t('nodata')}</p>`;return}
    const tot=list.reduce((s,b)=>s+b.total,0);
    $('billsBox').innerHTML=`<div class="tblwrap"><table class="tbl"><thead><tr><th>${t('billno')}</th><th>${t('time')}</th><th>${t('table')}</th><th>${t('sectionW')}</th><th>${t('items')}</th><th class="r">${t('total')}</th><th class="r">${t('actions')}</th></tr></thead><tbody>${
      list.map(b=>`<tr><td><b>#${n(b.id)}</b></td><td>${fmtTime(parseDT(b.created_at))}</td><td>${n(esc(b.table_no||'-'))}${b.customer?`<br><small class="muted">${esc(b.customer)}</small>`:''}</td>
        <td><span class="sbadge ${b.section}">${secIcon(b.section)} ${t('sec_'+b.section)}</span></td>
        <td><small>${b.items.map(l=>esc(nm(l))+(lv(l)?' ('+esc(lv(l))+')':'')+' ×'+n(l.qty)).join(', ')}</small></td>
        <td class="r"><b>${money(b.total)}</b></td>
        <td class="r" style="white-space:nowrap"><button class="icon" onclick="printBills([BILLS.find(x=>x.id===${b.id})])">${t('reprint')}</button><button class="icon danger" onclick="delBill(${b.id})">🗑</button></td></tr>`).join('')}
      <tr><td colspan="5" class="r"><b>${t('revenue')}</b></td><td class="r"><b style="color:var(--mar);font-size:18px">${money(tot)}</b></td><td></td></tr></tbody></table></div>`;
  }catch(e){toast(e.message,true)}
}
async function ensurePin(){
  if(PIN)return true;
  const p=prompt(t('pin'));if(!p)return false;
  try{await api('/api/login','POST',{pin:p});PIN=p;try{sessionStorage.setItem('ak_pin',p)}catch(e){};return true}
  catch(e){toast(t('wrongpin'),true);return false}
}
async function delBill(id){
  if(!confirm(t('confirmDel')+' #'+n(id)))return;
  if(!await ensurePin())return;
  try{await api('/api/bills/'+id,'DELETE');toast(t('deleted'));loadBills()}catch(e){toast(e.message,true)}
}

/* =================== ADMIN =================== */
function viewAdmin(){
  if(!PIN){
    $('view').innerHTML=`<section class="panel login"><h2 style="color:var(--mar);margin:0">🔐 ${t('signIn')}</h2>
      <input type="password" id="pinIn" inputmode="numeric" placeholder="••••" onkeydown="if(event.key==='Enter')doLogin()">
      <button class="btn pri" onclick="doLogin()">${t('login')}</button><p class="muted" style="margin:0">${t('pinHint')}</p></section>`;
    setTimeout(()=>$('pinIn')&&$('pinIn').focus(),50);return;
  }
  $('view').innerHTML=`<div class="atabs">${['menuitems','categories','settings'].map(k=>`<button class="${ATAB===k?'on':''}" onclick="ATAB='${k}';viewAdmin()">${t(k)}</button>`).join('')}
    <button class="ghost" onclick="logout()">🚪 ${t('logout')}</button></div><section class="panel" id="adminBox"></section>`;
  if(ATAB==='menuitems')adminItems();else if(ATAB==='categories')adminCats();else adminSettings();
}
async function doLogin(){
  const p=$('pinIn').value;
  try{await api('/api/login','POST',{pin:p});PIN=p;try{sessionStorage.setItem('ak_pin',p)}catch(e){};viewAdmin()}
  catch(e){toast(t('wrongpin'),true)}
}
function logout(){PIN='';try{sessionStorage.removeItem('ak_pin')}catch(e){};viewAdmin()}
async function reloadMenu(){MENU=await api('/api/menu')}

function adminItems(){
  const cats=MENU.categories.filter(c=>ASEC==='all'||c.section===ASEC);
  if(ACAT&&!cats.some(c=>c.id===ACAT))ACAT=0;
  $('adminBox').innerHTML=`<div class="ph"><h2>${t('menuitems')}</h2>
    <div class="seg2">${['all','hotel','bar'].map(k=>`<button class="${ASEC===k?'on':''}" onclick="ASEC='${k}';ACAT=0;adminItems()">${k==='all'?t('all'):secIcon(k)+' '+t('sec_'+k)}</button>`).join('')}</div>
    <select onchange="ACAT=+this.value;adminItemsTable()"><option value="0">${t('allCats')}</option>${cats.map(c=>`<option value="${c.id}" ${ACAT===c.id?'selected':''}>${esc(nm(c))}</option>`).join('')}</select>
    <input placeholder="🔍 ${esc(t('search'))}" value="${esc(AQ)}" oninput="AQ=this.value;adminItemsTable()">
    <button class="btn pri" onclick="editItem(0)">${t('additem')}</button></div><div class="tblwrap" id="aTable"></div>`;
  adminItemsTable();
}
function adminItemsTable(){
  const q=AQ.trim().toLowerCase();
  const items=MENU.items.filter(i=>(ASEC==='all'||i.section===ASEC)&&(!ACAT||i.category_id===ACAT)&&(!q||(i.name_mr+' '+i.name_en).toLowerCase().includes(q)));
  $('aTable').innerHTML=items.length?`<table class="tbl"><thead><tr><th></th><th>${t('name_mr')}</th><th>${t('name_en')}</th><th>${t('category')}</th><th>${t('variants')}</th><th>${t('active')}</th><th class="r">${t('actions')}</th></tr></thead><tbody>${
    items.map(i=>`<tr style="${i.active?'':'opacity:.5'}"><td><span class="dot ${i.type}"></span></td><td><b>${esc(i.name_mr)}</b></td><td>${esc(i.name_en)}</td><td><span class="sbadge ${i.section}">${secIcon(i.section)}</span> <small>${esc(catName(i.category_id))}</small></td>
      <td>${i.variants.map(v=>(vl(v)?`<span class="badge">${esc(vl(v))}</span> `:'')+'<b>'+money(v.p)+'</b>').join(' &nbsp; ')}</td>
      <td><label class="switch"><input type="checkbox" ${i.active?'checked':''} onchange="toggleActive(${i.id},this.checked)"><span></span></label></td>
      <td class="r" style="white-space:nowrap"><button class="icon" onclick="editItem(${i.id})">✏️ ${t('edit')}</button><button class="icon danger" onclick="delItem(${i.id})">🗑</button></td></tr>`).join('')}</tbody></table>`:`<p class="muted" style="text-align:center">${t('noItems')}</p>`;
}
async function toggleActive(id,on){
  const it=MENU.items.find(x=>x.id===id);
  try{await api('/api/items/'+id,'PUT',{...it,active:on?1:0});await reloadMenu();adminItemsTable();toast(t('saved'))}catch(e){toast(e.message,true)}
}
async function delItem(id){
  if(!confirm(t('confirmDel')))return;
  try{await api('/api/items/'+id,'DELETE');await reloadMenu();adminItemsTable();toast(t('deleted'))}catch(e){toast(e.message,true)}
}
function editItem(id){
  if(!MENU.categories.length){toast(t('addcat'),true);return}
  const it=id?MENU.items.find(x=>x.id===id):{name_mr:'',name_en:'',category_id:ACAT||(MENU.categories.find(c=>ASEC==='all'||c.section===ASEC)||MENU.categories[0]).id,type:'veg',variants:[{mr:'',en:'',p:''}],active:1};
  EDIT_VARS=JSON.parse(JSON.stringify(it.variants));
  openModal(`<h3>${id?'✏️ '+t('edit'):t('additem')}</h3>
   <div class="form">
    <label>${t('name_mr')}<input id="fMr" value="${esc(it.name_mr)}"></label>
    <label>${t('name_en')}<input id="fEn" value="${esc(it.name_en)}"></label>
    <label>${t('category')}<select id="fCat">${MENU.categories.map(c=>`<option value="${c.id}" ${c.id===it.category_id?'selected':''}>${secIcon(c.section)} ${esc(nm(c))}</option>`).join('')}</select></label>
    <label>${t('type')}<select id="fType"><option value="veg" ${it.type==='veg'?'selected':''}>🟢 ${t('veg')}</option><option value="nonveg" ${it.type==='nonveg'?'selected':''}>🔴 ${t('nonveg')}</option></select></label>
    <label class="chk full"><input type="checkbox" id="fAct" ${it.active?'checked':''}> ${t('active')}</label>
   </div>
   <h4>${t('variants')}</h4>
   <div class="presets"><button onclick="preset('s')">${t('single')}</button><button onclick="preset('hf')">${t('hf')}</button><button onclick="preset('phf')">${t('phf')}</button><button onclick="preset('sb')">${t('sb')}</button></div>
   <div class="vrow muted" style="font-size:12px;font-weight:700"><span>${t('label_mr')}</span><span>${t('label_en')}</span><span>${t('price')} (₹)</span><span></span></div>
   <div id="varRows"></div>
   <button class="ghost" onclick="EDIT_VARS.push({mr:'',en:'',p:''});renderVars()">${t('addvariant')}</button>
   <div class="mact"><button class="ghost" onclick="closeModal()">${t('cancel')}</button><button class="btn pri" onclick="saveItem(${id})">💾 ${t('saveBtn')}</button></div>`);
  renderVars();
}
function preset(k){
  const L={s:[['','']],hf:[['हाफ','Half'],['फुल','Full']],phf:[['प्लेट','Plate'],['हाफ','Half'],['फुल','Full']],sb:[['छोटी','Small'],['मोठी','Big']]}[k];
  EDIT_VARS=L.map((l,i)=>({mr:l[0],en:l[1],p:EDIT_VARS[i]?EDIT_VARS[i].p:''}));renderVars();
}
function renderVars(){
  $('varRows').innerHTML=EDIT_VARS.map((v,i)=>`<div class="vrow">
    <input value="${esc(v.mr)}" placeholder="—" oninput="EDIT_VARS[${i}].mr=this.value">
    <input value="${esc(v.en)}" placeholder="—" oninput="EDIT_VARS[${i}].en=this.value">
    <input type="number" min="0" value="${v.p}" placeholder="0" oninput="EDIT_VARS[${i}].p=this.value">
    <button class="icon danger" ${EDIT_VARS.length<2?'disabled':''} onclick="EDIT_VARS.splice(${i},1);renderVars()">✕</button></div>`).join('');
}
async function saveItem(id){
  const body={name_mr:$('fMr').value.trim(),name_en:$('fEn').value.trim(),category_id:+$('fCat').value,type:$('fType').value,active:$('fAct').checked?1:0,
    variants:EDIT_VARS.filter(v=>v.p!==''&&v.p!==null).map(v=>({mr:v.mr,en:v.en,p:Number(v.p)}))};
  if(!body.name_mr&&!body.name_en)return toast(t('nameRequired'),true);
  try{await api(id?'/api/items/'+id:'/api/items',id?'PUT':'POST',body);await reloadMenu();closeModal();adminItemsTable();toast(t('saved'))}catch(e){toast(e.message,true)}
}

function adminCats(){
  $('adminBox').innerHTML=`<div class="ph"><h2>${t('categories')}</h2><button class="btn pri" onclick="addCat()">${t('addcat')}</button></div>
   <div class="tblwrap"><table class="tbl"><thead><tr><th>${t('name_mr')}</th><th>${t('name_en')}</th><th style="width:130px">${t('sectionW')}</th><th style="width:90px">${t('sort')}</th><th class="r">${t('items')}</th><th class="r">${t('actions')}</th></tr></thead><tbody>${
    MENU.categories.map(c=>`<tr><td><input class="ci" id="cm${c.id}" value="${esc(c.name_mr)}"></td><td><input class="ci" id="ce${c.id}" value="${esc(c.name_en)}"></td>
     <td><select class="ci" id="csec${c.id}">${SECTIONS.map(x=>`<option value="${x}" ${c.section===x?'selected':''}>${secIcon(x)} ${t('sec_'+x)}</option>`).join('')}</select></td>
     <td><input class="ci" type="number" id="cs${c.id}" value="${c.sort}"></td><td class="r">${n(MENU.items.filter(i=>i.category_id===c.id).length)}</td>
     <td class="r" style="white-space:nowrap"><button class="icon" onclick="saveCat(${c.id})">💾 ${t('saveBtn')}</button><button class="icon danger" onclick="delCat(${c.id})">🗑</button></td></tr>`).join('')}</tbody></table></div>`;
}
function addCat(){
  openModal(`<h3>${t('addcat')}</h3><div class="form"><label>${t('name_mr')}<input id="ncm"></label><label>${t('name_en')}<input id="nce"></label>
   <label>${t('sectionW')}<select id="ncsec">${SECTIONS.map(x=>`<option value="${x}" ${ASEC===x?'selected':''}>${secIcon(x)} ${t('sec_'+x)}</option>`).join('')}</select></label>
   <label>${t('sort')}<input type="number" id="ncs" value="${(Math.max(0,...MENU.categories.map(c=>c.sort))+10)}"></label></div>
   <div class="mact"><button class="ghost" onclick="closeModal()">${t('cancel')}</button><button class="btn pri" onclick="saveCat(0)">💾 ${t('saveBtn')}</button></div>`);
}
async function saveCat(id){
  const body=id?{name_mr:$('cm'+id).value,name_en:$('ce'+id).value,sort:+$('cs'+id).value,section:$('csec'+id).value}:{name_mr:$('ncm').value,name_en:$('nce').value,sort:+$('ncs').value,section:$('ncsec').value};
  try{await api(id?'/api/categories/'+id:'/api/categories',id?'PUT':'POST',body);await reloadMenu();closeModal();adminCats();toast(t('saved'))}catch(e){toast(e.message,true)}
}
async function delCat(id){
  if(!confirm(t('confirmCatDel')))return;
  try{await api('/api/categories/'+id,'DELETE');await reloadMenu();adminCats();toast(t('deleted'))}catch(e){toast(e.message,true)}
}

function adminSettings(){
  const f=k=>`<label>${t(k)}<input id="s_${k}" value="${esc(SETTINGS[k]||'')}"></label>`;
  $('adminBox').innerHTML=`<div class="ph"><h2>${t('settings')}</h2></div>
   <div class="form">${['hotel_mr','hotel_en','tag_mr','tag_en','addr_mr','addr_en','phone','gstin','footer_mr','footer_en'].map(f).join('')}
    <label>${t('table_count')}<input id="s_table_count" type="number" min="1" max="99" value="${esc(SETTINGS.table_count||15)}"></label>
    <label>${t('paper')}<select id="s_paper">${[['58','58 mm'],['80','80 mm'],['a4',t('a4')]].map(([v,l])=>`<option value="${v}" ${SETTINGS.paper===v?'selected':''}>${l}</option>`).join('')}</select></label>
    <label>${t('newpin')}<input id="s_pin" type="password" inputmode="numeric" placeholder="••••"></label>
    <p class="muted full" style="margin:0">💡 ${t('printTip')}</p>
   </div>
   <div class="mact"><button class="btn pri" onclick="saveSettings()">💾 ${t('saveBtn')}</button></div>`;
}
async function saveSettings(){
  const body={};['hotel_mr','hotel_en','tag_mr','tag_en','addr_mr','addr_en','phone','gstin','footer_mr','footer_en','paper','table_count'].forEach(k=>body[k]=$('s_'+k).value);
  const np=$('s_pin').value.trim();if(np)body.new_pin=np;
  try{SETTINGS=await api('/api/settings','PUT',body);
    if(np){PIN=np;try{sessionStorage.setItem('ak_pin',np)}catch(e){};toast(t('pinChanged'))}else toast(t('settingsSaved'));
    render();
  }catch(e){toast(e.message,true)}
}

/* =================== START =================== */
(async function(){
  try{await loadAll()}catch(e){toast(e.message,true)}
  await pollOrders();
  render();
  setInterval(tickDay,30000);
  setInterval(pollOrders,5000);
  setInterval(()=>{if(VIEW==='tables')renderTablesBody()},30000);
})();
</script>
</body>
</html>
"""


# ------------------------------------------------------------------
#  START SERVER
# ------------------------------------------------------------------
def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def main():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = "http://localhost:{}".format(PORT)
    print("=" * 56)
    print("  Hotel Akshara Billing is running")
    print("  Open on this computer :  " + url)
    ip = lan_ip()
    if ip:
        print("  Network (phone/tablet):  http://{}:{}".format(ip, PORT))
    print("  Database file         :  " + DB_PATH)
    print("  Default Admin PIN     :  1234")
    print("  Press Ctrl + C to stop")
    print("=" * 56)
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
