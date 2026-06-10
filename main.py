import telebot
from telebot import types
import sqlite3
import os
import sys
import re
import requests
from datetime import datetime
from faker import Faker
import html
import phonenumbers
from phonenumbers import NumberParseException
import time

# --- আপনার দেওয়া ভ্যালু দিয়ে আপডেট করা হয়েছে ---
# BOT_TOKEN এবং অন্যান্য MAYTAPI ভেরিয়েবলগুলো এখন সরাসরি কোডে অ্যাসাইন করা হয়েছে
# সিকিউরিটির জন্য, ভবিষ্যতে এগুলো environment variable হিসেবে ব্যবহার করার পরামর্শ দেওয়া হচ্ছে।

BOT_TOKEN = '7537002718:AAFX9ANbMQgVJQ8UgHWsBEL14BrtO4zE0vQ'
MAYTAPI_PRODUCT_ID = '11ef3df6-00f1-4a11-a1a2-0f703175f87e'
MAYTAPI_PHONE_ID = '123542'
MAYTAPI_TOKEN = 'b3de65b5-0b07-411a-b0c4-830d3a2c9c6b'


ADMIN_CHAT_ID = 5810613583
OTP_GROUP_LINK = "https://t.me/+E7_2faWu-_wyMDZl"

REQUIRED_CHANNELS = [
    {
        'id': -1002383687280,
        'link': 'https://t.me/+gljurDGhpn4xMjNl',
        'name': 'Channel'
    },
    {
        'id': -1002491404165,
        'link': 'https://t.me/+PWbzmHgGdXM2ZWJl',
        'name': 'Group'
    }
]

bot = telebot.TeleBot(BOT_TOKEN)

def init_db():
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            service_type TEXT NOT NULL,
            is_assigned INTEGER DEFAULT 0,
            assigned_to INTEGER,
            assigned_at TEXT,
            UNIQUE(phone_number, service_type)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            number_id INTEGER NOT NULL,
            assigned_at TEXT NOT NULL,
            FOREIGN KEY (number_id) REFERENCES numbers (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TEXT NOT NULL,
            language TEXT DEFAULT 'en'
        )
    ''')

    try:
        cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT "en"')
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

admin_state = {}
user_temp_emails = {}
user_email_tokens = {}
user_selected_provider = {}
user_whatsapp_check_state = {}
user_country_lookup_state = {}
user_fake_address_state = {}

COUNTRY_DATA = {
    "Afghanistan": {"alpha2": "AF", "alpha3": "AFG", "numeric": "004"},
    "Albania": {"alpha2": "AL", "alpha3": "ALB", "numeric": "008"},
    "Algeria": {"alpha2": "DZ", "alpha3": "DZA", "numeric": "012"},
    "American Samoa": {"alpha2": "AS", "alpha3": "ASM", "numeric": "016"},
    "Andorra": {"alpha2": "AD", "alpha3": "AND", "numeric": "020"},
    "Angola": {"alpha2": "AO", "alpha3": "AGO", "numeric": "024"},
    "Anguilla": {"alpha2": "AI", "alpha3": "AIA", "numeric": "660"},
    "Antarctica": {"alpha2": "AQ", "alpha3": "ATA", "numeric": "010"},
    "Antigua and Barbuda": {"alpha2": "AG", "alpha3": "ATG", "numeric": "028"},
    "Argentina": {"alpha2": "AR", "alpha3": "ARG", "numeric": "032"},
    "Armenia": {"alpha2": "AM", "alpha3": "ARM", "numeric": "051"},
    "Aruba": {"alpha2": "AW", "alpha3": "ABW", "numeric": "533"},
    "Australia": {"alpha2": "AU", "alpha3": "AUS", "numeric": "036"},
    "Austria": {"alpha2": "AT", "alpha3": "AUT", "numeric": "040"},
    "Azerbaijan": {"alpha2": "AZ", "alpha3": "AZE", "numeric": "031"},
    "Bahamas (the)": {"alpha2": "BS", "alpha3": "BHS", "numeric": "044"},
    "Bahrain": {"alpha2": "BH", "alpha3": "BHR", "numeric": "048"},
    "Bangladesh": {"alpha2": "BD", "alpha3": "BGD", "numeric": "050"},
    "Barbados": {"alpha2": "BB", "alpha3": "BRB", "numeric": "052"},
    "Belarus": {"alpha2": "BY", "alpha3": "BLR", "numeric": "112"},
    "Belgium": {"alpha2": "BE", "alpha3": "BEL", "numeric": "056"},
    "Belize": {"alpha2": "BZ", "alpha3": "BLZ", "numeric": "084"},
    "Benin": {"alpha2": "BJ", "alpha3": "BEN", "numeric": "204"},
    "Bermuda": {"alpha2": "BM", "alpha3": "BMU", "numeric": "060"},
    "Bhutan": {"alpha2": "BT", "alpha3": "BTN", "numeric": "064"},
    "Bolivia (Plurinational State of)": {"alpha2": "BO", "alpha3": "BOL", "numeric": "068"},
    "Bonaire, Sint Eustatius and Saba": {"alpha2": "BQ", "alpha3": "BES", "numeric": "535"},
    "Bosnia and Herzegovina": {"alpha2": "BA", "alpha3": "BIH", "numeric": "070"},
    "Botswana": {"alpha2": "BW", "alpha3": "BWA", "numeric": "072"},
    "Bouvet Island": {"alpha2": "BV", "alpha3": "BVT", "numeric": "074"},
    "Brazil": {"alpha2": "BR", "alpha3": "BRA", "numeric": "076"},
    "British Indian Ocean Territory (the)": {"alpha2": "IO", "alpha3": "IOT", "numeric": "086"},
    "Brunei Darussalam": {"alpha2": "BN", "alpha3": "BRN", "numeric": "096"},
    "Bulgaria": {"alpha2": "BG", "alpha3": "BGR", "numeric": "100"},
    "Burkina Faso": {"alpha2": "BF", "alpha3": "BFA", "numeric": "854"},
    "Burundi": {"alpha2": "BI", "alpha3": "BDI", "numeric": "108"},
    "Cabo Verde": {"alpha2": "CV", "alpha3": "CPV", "numeric": "132"},
    "Cambodia": {"alpha2": "KH", "alpha3": "KHM", "numeric": "116"},
    "Cameroon": {"alpha2": "CM", "alpha3": "CMR", "numeric": "120"},
    "Canada": {"alpha2": "CA", "alpha3": "CAN", "numeric": "124"},
    "Cayman Islands (the)": {"alpha2": "KY", "alpha3": "CYM", "numeric": "136"},
    "Central African Republic (the)": {"alpha2": "CF", "alpha3": "CAF", "numeric": "140"},
    "Chad": {"alpha2": "TD", "alpha3": "TCD", "numeric": "148"},
    "Chile": {"alpha2": "CL", "alpha3": "CHL", "numeric": "152"},
    "China": {"alpha2": "CN", "alpha3": "CHN", "numeric": "156"},
    "Christmas Island": {"alpha2": "CX", "alpha3": "CXR", "numeric": "162"},
    "Cocos (Keeling) Islands (the)": {"alpha2": "CC", "alpha3": "CCK", "numeric": "166"},
    "Colombia": {"alpha2": "CO", "alpha3": "COL", "numeric": "170"},
    "Comoros (the)": {"alpha2": "KM", "alpha3": "COM", "numeric": "174"},
    "Congo (the Democratic Republic of the)": {"alpha2": "CD", "alpha3": "COD", "numeric": "180"},
    "Congo (the)": {"alpha2": "CG", "alpha3": "COG", "numeric": "178"},
    "Cook Islands (the)": {"alpha2": "CK", "alpha3": "COK", "numeric": "184"},
    "Costa Rica": {"alpha2": "CR", "alpha3": "CRI", "numeric": "188"},
    "Croatia": {"alpha2": "HR", "alpha3": "HRV", "numeric": "191"},
    "Cuba": {"alpha2": "CU", "alpha3": "CUB", "numeric": "192"},
    "Curaçao": {"alpha2": "CW", "alpha3": "CUW", "numeric": "531"},
    "Cyprus": {"alpha2": "CY", "alpha3": "CYP", "numeric": "196"},
    "Czechia": {"alpha2": "CZ", "alpha3": "CZE", "numeric": "203"},
    "Côte d'Ivoire": {"alpha2": "CI", "alpha3": "CIV", "numeric": "384"},
    "Denmark": {"alpha2": "DK", "alpha3": "DNK", "numeric": "208"},
    "Djibouti": {"alpha2": "DJ", "alpha3": "DJI", "numeric": "262"},
    "Dominica": {"alpha2": "DM", "alpha3": "DMA", "numeric": "212"},
    "Dominican Republic (the)": {"alpha2": "DO", "alpha3": "DOM", "numeric": "214"},
    "Ecuador": {"alpha2": "EC", "alpha3": "ECU", "numeric": "218"},
    "Egypt": {"alpha2": "EG", "alpha3": "EGY", "numeric": "818"},
    "El Salvador": {"alpha2": "SV", "alpha3": "SLV", "numeric": "222"},
    "Equatorial Guinea": {"alpha2": "GQ", "alpha3": "GNQ", "numeric": "226"},
    "Eritrea": {"alpha2": "ER", "alpha3": "ERI", "numeric": "232"},
    "Estonia": {"alpha2": "EE", "alpha3": "EST", "numeric": "233"},
    "Eswatini": {"alpha2": "SZ", "alpha3": "SWZ", "numeric": "748"},
    "Ethiopia": {"alpha2": "ET", "alpha3": "ETH", "numeric": "231"},
    "Falkland Islands (the) [Malvinas]": {"alpha2": "FK", "alpha3": "FLK", "numeric": "238"},
    "Faroe Islands (the)": {"alpha2": "FO", "alpha3": "FRO", "numeric": "234"},
    "Fiji": {"alpha2": "FJ", "alpha3": "FJI", "numeric": "242"},
    "Finland": {"alpha2": "FI", "alpha3": "FIN", "numeric": "246"},
    "France": {"alpha2": "FR", "alpha3": "FRA", "numeric": "250"},
    "French Guiana": {"alpha2": "GF", "alpha3": "GUF", "numeric": "254"},
    "French Polynesia": {"alpha2": "PF", "alpha3": "PYF", "numeric": "258"},
    "French Southern Territories (the)": {"alpha2": "TF", "alpha3": "ATF", "numeric": "260"},
    "Gabon": {"alpha2": "GA", "alpha3": "GAB", "numeric": "266"},
    "Gambia (the)": {"alpha2": "GM", "alpha3": "GMB", "numeric": "270"},
    "Georgia": {"alpha2": "GE", "alpha3": "GEO", "numeric": "268"},
    "Germany": {"alpha2": "DE", "alpha3": "DEU", "numeric": "276"},
    "Ghana": {"alpha2": "GH", "alpha3": "GHA", "numeric": "288"},
    "Gibraltar": {"alpha2": "GI", "alpha3": "GIB", "numeric": "292"},
    "Greece": {"alpha2": "GR", "alpha3": "GRC", "numeric": "300"},
    "Greenland": {"alpha2": "GL", "alpha3": "GRL", "numeric": "304"},
    "Grenada": {"alpha2": "GD", "alpha3": "GRD", "numeric": "308"},
    "Guadeloupe": {"alpha2": "GP", "alpha3": "GLP", "numeric": "312"},
    "Guam": {"alpha2": "GU", "alpha3": "GUM", "numeric": "316"},
    "Guatemala": {"alpha2": "GT", "alpha3": "GTM", "numeric": "320"},
    "Guernsey": {"alpha2": "GG", "alpha3": "GGY", "numeric": "831"},
    "Guinea": {"alpha2": "GN", "alpha3": "GIN", "numeric": "324"},
    "Guinea-Bissau": {"alpha2": "GW", "alpha3": "GNB", "numeric": "624"},
    "Guyana": {"alpha2": "GY", "alpha3": "GUY", "numeric": "328"},
    "Haiti": {"alpha2": "HT", "alpha3": "HTI", "numeric": "332"},
    "Heard Island and McDonald Islands": {"alpha2": "HM", "alpha3": "HMD", "numeric": "334"},
    "Holy See (the)": {"alpha2": "VA", "alpha3": "VAT", "numeric": "336"},
    "Honduras": {"alpha2": "HN", "alpha3": "HND", "numeric": "340"},
    "Hong Kong": {"alpha2": "HK", "alpha3": "HKG", "numeric": "344"},
    "Hungary": {"alpha2": "HU", "alpha3": "HUN", "numeric": "348"},
    "Iceland": {"alpha2": "IS", "alpha3": "ISL", "numeric": "352"},
    "India": {"alpha2": "IN", "alpha3": "IND", "numeric": "356"},
    "Indonesia": {"alpha2": "ID", "alpha3": "IDN", "numeric": "360"},
    "Iran (Islamic Republic of)": {"alpha2": "IR", "alpha3": "IRN", "numeric": "364"},
    "Iraq": {"alpha2": "IQ", "alpha3": "IRQ", "numeric": "368"},
    "Ireland": {"alpha2": "IE", "alpha3": "IRL", "numeric": "372"},
    "Isle of Man": {"alpha2": "IM", "alpha3": "IMN", "numeric": "833"},
    "Israel": {"alpha2": "IL", "alpha3": "ISR", "numeric": "376"},
    "Italy": {"alpha2": "IT", "alpha3": "ITA", "numeric": "380"},
    "Jamaica": {"alpha2": "JM", "alpha3": "JAM", "numeric": "388"},
    "Japan": {"alpha2": "JP", "alpha3": "JPN", "numeric": "392"},
    "Jersey": {"alpha2": "JE", "alpha3": "JEY", "numeric": "832"},
    "Jordan": {"alpha2": "JO", "alpha3": "JOR", "numeric": "400"},
    "Kazakhstan": {"alpha2": "KZ", "alpha3": "KAZ", "numeric": "398"},
    "Kenya": {"alpha2": "KE", "alpha3": "KEN", "numeric": "404"},
    "Kiribati": {"alpha2": "KI", "alpha3": "KIR", "numeric": "296"},
    "Korea (the Democratic People's Republic of)": {"alpha2": "KP", "alpha3": "PRK", "numeric": "408"},
    "Korea (the Republic of)": {"alpha2": "KR", "alpha3": "KOR", "numeric": "410"},
    "Kuwait": {"alpha2": "KW", "alpha3": "KWT", "numeric": "414"},
    "Kyrgyzstan": {"alpha2": "KG", "alpha3": "KGZ", "numeric": "417"},
    "Lao People's Democratic Republic (the)": {"alpha2": "LA", "alpha3": "LAO", "numeric": "418"},
    "Latvia": {"alpha2": "LV", "alpha3": "LVA", "numeric": "428"},
    "Lebanon": {"alpha2": "LB", "alpha3": "LBN", "numeric": "422"},
    "Lesotho": {"alpha2": "LS", "alpha3": "LSO", "numeric": "426"},
    "Liberia": {"alpha2": "LR", "alpha3": "LBR", "numeric": "430"},
    "Libya": {"alpha2": "LY", "alpha3": "LBY", "numeric": "434"},
    "Liechtenstein": {"alpha2": "LI", "alpha3": "LIE", "numeric": "438"},
    "Lithuania": {"alpha2": "LT", "alpha3": "LTU", "numeric": "440"},
    "Luxembourg": {"alpha2": "LU", "alpha3": "LUX", "numeric": "442"},
    "Macao": {"alpha2": "MO", "alpha3": "MAC", "numeric": "446"},
    "Madagascar": {"alpha2": "MG", "alpha3": "MDG", "numeric": "450"},
    "Malawi": {"alpha2": "MW", "alpha3": "MWI", "numeric": "454"},
    "Malaysia": {"alpha2": "MY", "alpha3": "MYS", "numeric": "458"},
    "Maldives": {"alpha2": "MV", "alpha3": "MDV", "numeric": "462"},
    "Mali": {"alpha2": "ML", "alpha3": "MLI", "numeric": "466"},
    "Malta": {"alpha2": "MT", "alpha3": "MLT", "numeric": "470"},
    "Marshall Islands (the)": {"alpha2": "MH", "alpha3": "MHL", "numeric": "584"},
    "Martinique": {"alpha2": "MQ", "alpha3": "MTQ", "numeric": "474"},
    "Mauritania": {"alpha2": "MR", "alpha3": "MRT", "numeric": "478"},
    "Mauritius": {"alpha2": "MU", "alpha3": "MUS", "numeric": "480"},
    "Mayotte": {"alpha2": "YT", "alpha3": "MYT", "numeric": "175"},
    "Mexico": {"alpha2": "MX", "alpha3": "MEX", "numeric": "484"},
    "Micronesia (Federated States of)": {"alpha2": "FM", "alpha3": "FSM", "numeric": "583"},
    "Moldova (the Republic of)": {"alpha2": "MD", "alpha3": "MDA", "numeric": "498"},
    "Monaco": {"alpha2": "MC", "alpha3": "MCO", "numeric": "492"},
    "Mongolia": {"alpha2": "MN", "alpha3": "MNG", "numeric": "496"},
    "Montenegro": {"alpha2": "ME", "alpha3": "MNE", "numeric": "499"},
    "Montserrat": {"alpha2": "MS", "alpha3": "MSR", "numeric": "500"},
    "Morocco": {"alpha2": "MA", "alpha3": "MAR", "numeric": "504"},
    "Mozambique": {"alpha2": "MZ", "alpha3": "MOZ", "numeric": "508"},
    "Myanmar": {"alpha2": "MM", "alpha3": "MMR", "numeric": "104"},
    "Namibia": {"alpha2": "NA", "alpha3": "NAM", "numeric": "516"},
    "Nauru": {"alpha2": "NR", "alpha3": "NRU", "numeric": "520"},
    "Nepal": {"alpha2": "NP", "alpha3": "NPL", "numeric": "524"},
    "Netherlands (the)": {"alpha2": "NL", "alpha3": "NLD", "numeric": "528"},
    "New Caledonia": {"alpha2": "NC", "alpha3": "NCL", "numeric": "540"},
    "New Zealand": {"alpha2": "NZ", "alpha3": "NZL", "numeric": "554"},
    "Nicaragua": {"alpha2": "NI", "alpha3": "NIC", "numeric": "558"},
    "Niger (the)": {"alpha2": "NE", "alpha3": "NER", "numeric": "562"},
    "Nigeria": {"alpha2": "NG", "alpha3": "NGA", "numeric": "566"},
    "Niue": {"alpha2": "NU", "alpha3": "NIU", "numeric": "570"},
    "Norfolk Island": {"alpha2": "NF", "alpha3": "NFK", "numeric": "574"},
    "Northern Mariana Islands (the)": {"alpha2": "MP", "alpha3": "MNP", "numeric": "580"},
    "Norway": {"alpha2": "NO", "alpha3": "NOR", "numeric": "578"},
    "Oman": {"alpha2": "OM", "alpha3": "OMN", "numeric": "512"},
    "Pakistan": {"alpha2": "PK", "alpha3": "PAK", "numeric": "586"},
    "Palau": {"alpha2": "PW", "alpha3": "PLW", "numeric": "585"},
    "Palestine, State of": {"alpha2": "PS", "alpha3": "PSE", "numeric": "275"},
    "Panama": {"alpha2": "PA", "alpha3": "PAN", "numeric": "591"},
    "Papua New Guinea": {"alpha2": "PG", "alpha3": "PNG", "numeric": "598"},
    "Paraguay": {"alpha2": "PY", "alpha3": "PRY", "numeric": "600"},
    "Peru": {"alpha2": "PE", "alpha3": "PER", "numeric": "604"},
    "Philippines (the)": {"alpha2": "PH", "alpha3": "PHL", "numeric": "608"},
    "Pitcairn": {"alpha2": "PN", "alpha3": "PCN", "numeric": "612"},
    "Poland": {"alpha2": "PL", "alpha3": "POL", "numeric": "616"},
    "Portugal": {"alpha2": "PT", "alpha3": "PRT", "numeric": "620"},
    "Puerto Rico": {"alpha2": "PR", "alpha3": "PRI", "numeric": "630"},
    "Qatar": {"alpha2": "QA", "alpha3": "QAT", "numeric": "634"},
    "Republic of North Macedonia": {"alpha2": "MK", "alpha3": "MKD", "numeric": "807"},
    "Romania": {"alpha2": "RO", "alpha3": "ROU", "numeric": "642"},
    "Russian Federation (the)": {"alpha2": "RU", "alpha3": "RUS", "numeric": "643"},
    "Rwanda": {"alpha2": "RW", "alpha3": "RWA", "numeric": "646"},
    "Réunion": {"alpha2": "RE", "alpha3": "REU", "numeric": "638"},
    "Saint Barthélemy": {"alpha2": "BL", "alpha3": "BLM", "numeric": "652"},
    "Saint Helena, Ascension and Tristan da Cunha": {"alpha2": "SH", "alpha3": "SHN", "numeric": "654"},
    "Saint Kitts and Nevis": {"alpha2": "KN", "alpha3": "KNA", "numeric": "659"},
    "Saint Lucia": {"alpha2": "LC", "alpha3": "LCA", "numeric": "662"},
    "Saint Martin (French part)": {"alpha2": "MF", "alpha3": "MAF", "numeric": "663"},
    "Saint Pierre and Miquelon": {"alpha2": "PM", "alpha3": "SPM", "numeric": "666"},
    "Saint Vincent and the Grenadines": {"alpha2": "VC", "alpha3": "VCT", "numeric": "670"},
    "Samoa": {"alpha2": "WS", "alpha3": "WSM", "numeric": "882"},
    "San Marino": {"alpha2": "SM", "alpha3": "SMR", "numeric": "674"},
    "Sao Tome and Principe": {"alpha2": "ST", "alpha3": "STP", "numeric": "678"},
    "Saudi Arabia": {"alpha2": "SA", "alpha3": "SAU", "numeric": "682"},
    "Senegal": {"alpha2": "SN", "alpha3": "SEN", "numeric": "686"},
    "Serbia": {"alpha2": "RS", "alpha3": "SRB", "numeric": "688"},
    "Seychelles": {"alpha2": "SC", "alpha3": "SYC", "numeric": "690"},
    "Sierra Leone": {"alpha2": "SL", "alpha3": "SLE", "numeric": "694"},
    "Singapore": {"alpha2": "SG", "alpha3": "SGP", "numeric": "702"},
    "Sint Maarten (Dutch part)": {"alpha2": "SX", "alpha3": "SXM", "numeric": "534"},
    "Slovakia": {"alpha2": "SK", "alpha3": "SVK", "numeric": "703"},
    "Slovenia": {"alpha2": "SI", "alpha3": "SVN", "numeric": "705"},
    "Solomon Islands": {"alpha2": "SB", "alpha3": "SLB", "numeric": "090"},
    "Somalia": {"alpha2": "SO", "alpha3": "SOM", "numeric": "706"},
    "South Africa": {"alpha2": "ZA", "alpha3": "ZAF", "numeric": "710"},
    "South Georgia and the South Sandwich Islands": {"alpha2": "GS", "alpha3": "SGS", "numeric": "239"},
    "South Sudan": {"alpha2": "SS", "alpha3": "SSD", "numeric": "728"},
    "Spain": {"alpha2": "ES", "alpha3": "ESP", "numeric": "724"},
    "Sri Lanka": {"alpha2": "LK", "alpha3": "LKA", "numeric": "144"},
    "Sudan (the)": {"alpha2": "SD", "alpha3": "SDN", "numeric": "729"},
    "Suriname": {"alpha2": "SR", "alpha3": "SUR", "numeric": "740"},
    "Svalbard and Jan Mayen": {"alpha2": "SJ", "alpha3": "SJM", "numeric": "744"},
    "Sweden": {"alpha2": "SE", "alpha3": "SWE", "numeric": "752"},
    "Switzerland": {"alpha2": "CH", "alpha3": "CHE", "numeric": "756"},
    "Syrian Arab Republic": {"alpha2": "SY", "alpha3": "SYR", "numeric": "760"},
    "Taiwan (Province of China)": {"alpha2": "TW", "alpha3": "TWN", "numeric": "158"},
    "Tajikistan": {"alpha2": "TJ", "alpha3": "TJK", "numeric": "762"},
    "Tanzania, United Republic of": {"alpha2": "TZ", "alpha3": "TZA", "numeric": "834"},
    "Thailand": {"alpha2": "TH", "alpha3": "THA", "numeric": "764"},
    "Timor-Leste": {"alpha2": "TL", "alpha3": "TLS", "numeric": "626"},
    "Togo": {"alpha2": "TG", "alpha3": "TGO", "numeric": "768"},
    "Tokelau": {"alpha2": "TK", "alpha3": "TKL", "numeric": "772"},
    "Tonga": {"alpha2": "TO", "alpha3": "TON", "numeric": "776"},
    "Trinidad and Tobago": {"alpha2": "TT", "alpha3": "TTO", "numeric": "780"},
    "Tunisia": {"alpha2": "TN", "alpha3": "TUN", "numeric": "788"},
    "Turkey": {"alpha2": "TR", "alpha3": "TUR", "numeric": "792"},
    "Turkmenistan": {"alpha2": "TM", "alpha3": "TKM", "numeric": "795"},
    "Turks and Caicos Islands (the)": {"alpha2": "TC", "alpha3": "TCA", "numeric": "796"},
    "Tuvalu": {"alpha2": "TV", "alpha3": "TUV", "numeric": "798"},
    "Uganda": {"alpha2": "UG", "alpha3": "UGA", "numeric": "800"},
    "Ukraine": {"alpha2": "UA", "alpha3": "UKR", "numeric": "804"},
    "United Arab Emirates (the)": {"alpha2": "AE", "alpha3": "ARE", "numeric": "784"},
    "United Kingdom of Great Britain and Northern Ireland (the)": {"alpha2": "GB", "alpha3": "GBR", "numeric": "826"},
    "United States Minor Outlying Islands (the)": {"alpha2": "UM", "alpha3": "UMI", "numeric": "581"},
    "United States of America (the)": {"alpha2": "US", "alpha3": "USA", "numeric": "840"},
    "Uruguay": {"alpha2": "UY", "alpha3": "URY", "numeric": "858"},
    "Uzbekistan": {"alpha2": "UZ", "alpha3": "UZB", "numeric": "860"},
    "Vanuatu": {"alpha2": "VU", "alpha3": "VUT", "numeric": "548"},
    "Venezuela (Bolivarian Republic of)": {"alpha2": "VE", "alpha3": "VEN", "numeric": "862"},
    "Viet Nam": {"alpha2": "VN", "alpha3": "VNM", "numeric": "704"},
    "Virgin Islands (British)": {"alpha2": "VG", "alpha3": "VGB", "numeric": "092"},
    "Virgin Islands (U.S.)": {"alpha2": "VI", "alpha3": "VIR", "numeric": "850"},
    "Wallis and Futuna": {"alpha2": "WF", "alpha3": "WLF", "numeric": "876"},
    "Western Sahara": {"alpha2": "EH", "alpha3": "ESH", "numeric": "732"},
    "Yemen": {"alpha2": "YE", "alpha3": "YEM", "numeric": "887"},
    "Zambia": {"alpha2": "ZM", "alpha3": "ZMB", "numeric": "894"},
    "Zimbabwe": {"alpha2": "ZW", "alpha3": "ZWE", "numeric": "716"},
    "Åland Islands": {"alpha2": "AX", "alpha3": "ALA", "numeric": "248"}
}

TRANSLATIONS = {
    'bn': {
        'select_language': '🌍 আপনার ভাষা নির্বাচন করুন:',
        'language_changed': '✅ ভাষা সফলভাবে পরিবর্তন হয়েছে!',
        'welcome': '✅ স্বাগতম! একটি অপশন বেছে নিন:',
        'temp_mail': '📧 Temp mail',
        'temp_number': '📱 Temp number',
        'fake_address': '🏠 Fake address',
        'whatsapp_check': '✅ Whatsapp Chak',
        'country_shortname': '🌍 Country Short name',
        'admin_support': 'Admin support',
        'language_change': '🌐 ভাষা পরিবর্তন',
        'whatsapp_checker_title': '📱 WhatsApp Number Checker (100% Accurate)',
        'whatsapp_checker_desc': '✅ Detects WhatsApp Business accounts\n✅ সব দেশের নাম্বার support\n✅ Unlimited checking\n\nনাম্বার গুলো পাঠান:\n\nউদাহরণ:\nBangladesh 🇧🇩 8801862050745\nUSA 🇺🇸 14155552671\nPeru 🇵🇪 51927229717\n\n✨ এই checker 100% সঠিক ভাবে বলবে:\n• নাম্বারে WhatsApp আছে কিনা\n• WhatsApp Business কিনা\n• Message পাঠানো যাবে কিনা',
        'whatsapp_has': '✅ এই নাম্বারে WhatsApp আছে',
        'whatsapp_not_has': '❌ এই নাম্বারে WhatsApp নেই',
        'whatsapp_business': '💼 WhatsApp Business',
        'whatsapp_personal': '👤 Personal WhatsApp',
        'can_receive_msg': '✅ Message পাঠানো যাবে',
        'cannot_receive_msg': '❌ Message পাঠানো যাবে না',
        'no_numbers_found': '❌ কোন নাম্বার পাওয়া যায়নি!\n\nআবার চেষ্টা করুন।',
        'checking_progress': 'রিসিভ',
        'checking_wait': 'নাম্বার\n\n🔍 Checking via Maytapi API...\nঅপেক্ষা করুন...',
        'checking_status': 'Checking',
        'whatsapp_results': '📊 WhatsApp Number Check Results\n\nTotal Checked:',
        'whatsapp_personal_list': '✅ WhatsApp Personal',
        'whatsapp_business_list': '💼 WhatsApp Business',
        'no_whatsapp_list': '❌ No WhatsApp',
        'invalid_numbers_list': '⚠️ Invalid Numbers',
        'api_errors_list': '❔ API Errors',
        'powered_by': '✨ Powered by Maytapi WhatsApp API\n✅ 100% Accurate Real-time Verification',
    },
    'en': {
        'select_language': '🌍 Select your language:',
        'language_changed': '✅ Language changed successfully!',
        'welcome': '✅ Welcome! Choose an option:',
        'temp_mail': '📧 Temp mail',
        'temp_number': '📱 Temp number',
        'fake_address': '🏠 Fake address',
        'whatsapp_check': '✅ Whatsapp Check',
        'country_shortname': '🌍 Country Short name',
        'admin_support': 'Admin support',
        'language_change': '🌐 Language Change',
        'whatsapp_checker_title': '📱 WhatsApp Number Checker (100% Accurate)',
        'whatsapp_checker_desc': '✅ Detects WhatsApp Business accounts\n✅ All country numbers supported\n✅ Unlimited checking\n\nSend numbers:\n\nExamples:\nBangladesh 🇧🇩 8801862050745\nUSA 🇺🇸 14155552671\nPeru 🇵🇪 51927229717\n\n✨ This checker will accurately tell you:\n• Whether the number has WhatsApp\n• Whether it\'s WhatsApp Business\n• Whether messages can be sent',
        'whatsapp_has': '✅ This number has WhatsApp',
        'whatsapp_not_has': '❌ This number does not have WhatsApp',
        'whatsapp_business': '💼 WhatsApp Business',
        'whatsapp_personal': '👤 Personal WhatsApp',
        'can_receive_msg': '✅ Can receive messages',
        'cannot_receive_msg': '❌ Cannot receive messages',
        'no_numbers_found': '❌ No numbers found!\n\nPlease try again.',
        'checking_progress': 'Received',
        'checking_wait': 'numbers\n\n🔍 Checking via Maytapi API...\nPlease wait...',
        'checking_status': 'Checking',
        'whatsapp_results': '📊 WhatsApp Number Check Results\n\nTotal Checked:',
        'whatsapp_personal_list': '✅ WhatsApp Personal',
        'whatsapp_business_list': '💼 WhatsApp Business',
        'no_whatsapp_list': '❌ No WhatsApp',
        'invalid_numbers_list': '⚠️ Invalid Numbers',
        'api_errors_list': '❔ API Errors',
        'powered_by': '✨ Powered by Maytapi WhatsApp API\n✅ 100% Accurate Real-time Verification',
    },
    'ru': {
        'select_language': '🌍 Выберите ваш язык:',
        'language_changed': '✅ Язык успешно изменен!',
        'welcome': '✅ Добро пожаловать! Выберите опцию:',
        'temp_mail': '📧 Temp mail',
        'temp_number': '📱 Temp number',
        'fake_address': '🏠 Fake address',
        'whatsapp_check': '✅ Whatsapp проверка',
        'country_shortname': '🌍 Country Short name',
        'admin_support': 'Admin support',
        'language_change': '🌐 Изменить язык',
        'whatsapp_checker_title': '📱 WhatsApp Number Checker (100% Accurate)',
        'whatsapp_checker_desc': '✅ Detects WhatsApp Business accounts\n✅ Поддержка номеров всех стран\n✅ Unlimited checking\n\nОтправьте номера:\n\nПримеры:\nBangladesh 🇧🇩 8801862050745\nUSA 🇺🇸 14155552671\nPeru 🇵🇪 51927229717\n\n✨ Этот инструмент точно скажет вам:\n• Есть ли у номера WhatsApp\n• Является ли это WhatsApp Business\n• Можно ли отправлять сообщения',
        'whatsapp_has': '✅ У этого номера есть WhatsApp',
        'whatsapp_not_has': '❌ У этого номера нет WhatsApp',
        'whatsapp_business': '💼 WhatsApp Business',
        'whatsapp_personal': '👤 Личный WhatsApp',
        'can_receive_msg': '✅ Может получать сообщения',
        'cannot_receive_msg': '❌ Не может получать сообщения',
        'no_numbers_found': '❌ Номера не найдены!\n\nПожалуйста, попробуйте снова.',
        'checking_progress': 'Получено',
        'checking_wait': 'номеров\n\n🔍 Checking via Maytapi API...\nПодождите...',
        'checking_status': 'Проверка',
        'whatsapp_results': '📊 WhatsApp Number Check Results\n\nTotal Checked:',
        'whatsapp_personal_list': '✅ WhatsApp Personal',
        'whatsapp_business_list': '💼 WhatsApp Business',
        'no_whatsapp_list': '❌ No WhatsApp',
        'invalid_numbers_list': '⚠️ Invalid Numbers',
        'api_errors_list': '❔ API Errors',
        'powered_by': '✨ Powered by Maytapi WhatsApp API\n✅ 100% Accurate Real-time Verification',
    },
    'hi': {
        'select_language': '🌍 अपनी भाषा चुनें:',
        'language_changed': '✅ भाषा सफलतापूर्वक बदली गई!',
        'welcome': '✅ स्वागत है! एक विकल्प चुनें:',
        'temp_mail': '📧 Temp mail',
        'temp_number': '📱 Temp number',
        'fake_address': '🏠 Fake address',
        'whatsapp_check': '✅ Whatsapp जाँच',
        'country_shortname': '🌍 Country Short name',
        'admin_support': 'Admin support',
        'language_change': '🌐 भाषा बदलें',
        'whatsapp_checker_title': '📱 WhatsApp Number Checker (100% Accurate)',
        'whatsapp_checker_desc': '✅ Detects WhatsApp Business accounts\n✅ सभी देशों के नंबर समर्थित\n✅ Unlimited checking\n\nनंबर भेजें:\n\nउदाहरण:\nBangladesh 🇧🇩 8801862050745\nUSA 🇺🇸 14155552671\nPeru 🇵🇪 51927229717\n\n✨ यह चेकर सटीक रूप से बताएगा:\n• नंबर पर WhatsApp है या नहीं\n• WhatsApp Business है या नहीं\n• संदेश भेजे जा सकते हैं या नहीं',
        'whatsapp_has': '✅ इस नंबर पर WhatsApp है',
        'whatsapp_not_has': '❌ इस नंबर पर WhatsApp नहीं है',
        'whatsapp_business': '💼 WhatsApp Business',
        'whatsapp_personal': '👤 व्यक्तिगत WhatsApp',
        'can_receive_msg': '✅ संदेश प्राप्त कर सकते हैं',
        'cannot_receive_msg': '❌ संदेश प्राप्त नहीं कर सकते',
        'no_numbers_found': '❌ कोई नंबर नहीं मिला!\n\nकृपया पुनः प्रयास करें।',
        'checking_progress': 'प्राप्त',
        'checking_wait': 'नंबर\n\n🔍 Checking via Maytapi API...\nकृपया प्रतीक्षा करें...',
        'checking_status': 'जाँच',
        'whatsapp_results': '📊 WhatsApp Number Check Results\n\nTotal Checked:',
        'whatsapp_personal_list': '✅ WhatsApp Personal',
        'whatsapp_business_list': '💼 WhatsApp Business',
        'no_whatsapp_list': '❌ No WhatsApp',
        'invalid_numbers_list': '⚠️ Invalid Numbers',
        'api_errors_list': '❔ API Errors',
        'powered_by': '✨ Powered by Maytapi WhatsApp API\n✅ 100% Accurate Real-time Verification',
    },
    'ar': {
        'select_language': '🌍 اختر لغتك:',
        'language_changed': '✅ تم تغيير اللغة بنجاح!',
        'welcome': '✅ مرحبا! اختر خيارا:',
        'temp_mail': '📧 Temp mail',
        'temp_number': '📱 Temp number',
        'fake_address': '🏠 Fake address',
        'whatsapp_check': '✅ فحص Whatsapp',
        'country_shortname': '🌍 Country Short name',
        'admin_support': 'Admin support',
        'language_change': '🌐 تغيير اللغة',
        'whatsapp_checker_title': '📱 WhatsApp Number Checker (100% Accurate)',
        'whatsapp_checker_desc': '✅ Detects WhatsApp Business accounts\n✅ دعم أرقام جميع الدول\n✅ Unlimited checking\n\nأرسل الأرقام:\n\nأمثلة:\nBangladesh 🇧🇩 8801862050745\nUSA 🇺🇸 14155552671\nPeru 🇵🇪 51927229717\n\n✨ سيخبرك هذا الفاحص بدقة:\n• ما إذا كان الرقم يحتوي على WhatsApp\n• ما إذا كان WhatsApp Business\n• ما إذا كان يمكن إرسال الرسائل',
        'whatsapp_has': '✅ هذا الرقم لديه WhatsApp',
        'whatsapp_not_has': '❌ هذا الرقم ليس لديه WhatsApp',
        'whatsapp_business': '💼 WhatsApp Business',
        'whatsapp_personal': '👤 WhatsApp شخصي',
        'can_receive_msg': '✅ يمكن استقبال الرسائل',
        'cannot_receive_msg': '❌ لا يمكن استقبال الرسائل',
        'no_numbers_found': '❌ لم يتم العثور على أرقام!\n\nالرجاء المحاولة مرة أخرى.',
        'checking_progress': 'تم الاستلام',
        'checking_wait': 'أرقام\n\n🔍 Checking via Maytapi API...\nيرجى الانتظار...',
        'checking_status': 'التحقق',
        'whatsapp_results': '📊 WhatsApp Number Check Results\n\nTotal Checked:',
        'whatsapp_personal_list': '✅ WhatsApp Personal',
        'whatsapp_business_list': '💼 WhatsApp Business',
        'no_whatsapp_list': '❌ No WhatsApp',
        'invalid_numbers_list': '⚠️ Invalid Numbers',
        'api_errors_list': '❔ API Errors',
        'powered_by': '✨ Powered by Maytapi WhatsApp API\n✅ 100% Accurate Real-time Verification',
    }
}

def get_user_language(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result and result[0] else 'en'
    except:
        return 'en'

def set_user_language(user_id, language):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def t(user_id, key):
    lang = get_user_language(user_id)
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, TRANSLATIONS['en'].get(key, key))

def register_user(user_id, username, first_name, last_name):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if not existing:
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, joined_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, now))
            conn.commit()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            
            conn.close()
            return True, user_count
        
        conn.close()
        return False, 0
    except Exception as e:
        return False, 0

def get_all_user_ids():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]
    except:
        return []

TEMP_MAIL_PROVIDERS = {
    'guerrilla': {
        'name': '✅ Guerrillamail (সবচেয়ে নির্ভরযোগ্য)',
        'domain': 'guerrillamail.com',
        'api_base': 'https://api.guerrillamail.com/ajax.php',
        'type': 'guerrilla'
    },
    'mailtm_1': {
        'name': '⚡ Mail.tm - Fast',
        'api_base': 'https://api.mail.tm',
        'type': 'mailtm'
    },
    'mailtm_2': {
        'name': '🚀 Mail.tm - Ultra',
        'api_base': 'https://api.mail.tm',
        'type': 'mailtm'
    },
    'mailtm_3': {
        'name': '💨 Mail.tm - Speed',
        'api_base': 'https://api.mail.tm',
        'type': 'mailtm'
    }
}

mailtm_domains_cache = {'domains': [], 'last_fetched': 0}

def fetch_mailtm_domains():
    """Fetch available domains from Mail.tm API with caching"""
    import time
    
    current_time = time.time()
    if mailtm_domains_cache['domains'] and (current_time - mailtm_domains_cache['last_fetched'] < 300):
        return mailtm_domains_cache['domains']
    
    try:
        response = requests.get('https://api.mail.tm/domains', timeout=10)
        if response.status_code == 200:
            data = response.json()
            domains_list = data.get('hydra:member', [])
            active_domains = [d['domain'] for d in domains_list if d.get('isActive', True)]
            
            if active_domains:
                mailtm_domains_cache['domains'] = active_domains
                mailtm_domains_cache['last_fetched'] = current_time
                print(f"Fetched {len(active_domains)} active domains from Mail.tm")
                return active_domains
    except Exception as e:
        print(f"Error fetching Mail.tm domains: {e}")
    
    return []

def check_user_membership(user_id):
    """Check if user is a member of all required channels"""
    not_joined = []

    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel['id'], user_id)
            if member.status in ['left', 'kicked']:
                not_joined.append(channel)
        except Exception as e:
            not_joined.append(channel)

    return not_joined

def create_join_buttons():
    """Create inline keyboard with join channel buttons"""
    markup = types.InlineKeyboardMarkup()

    for channel in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(
            f"Join {channel['name']}",
            url=channel['link']
        ))

    markup.add(types.InlineKeyboardButton(
        "✅ All Channels Joined",
        callback_data="check_membership"
    ))

    return markup

def is_user_member(user_id):
    """Check if user is member of all channels (returns True/False)"""
    if user_id == ADMIN_CHAT_ID:
        return True

    not_joined = check_user_membership(user_id)
    return len(not_joined) == 0

def require_membership(handler_func):
    """Decorator to enforce channel membership for message handlers"""
    def wrapper(message):
        user_id = message.chat.id

        if not is_user_member(user_id):
            bot.send_message(
                user_id,
                "❌ You must join all channels first to use this bot!",
                reply_markup=create_join_buttons()
            )
            return

        return handler_func(message)

    return wrapper

def require_membership_callback(handler_func):
    """Decorator to enforce channel membership for callback query handlers"""
    def wrapper(call):
        user_id = call.message.chat.id

        if not is_user_member(user_id):
            bot.answer_callback_query(
                call.id,
                "❌ You must join all channels to use this bot!",
                show_alert=True
            )
            bot.send_message(
                user_id,
                "❌ You must join all channels first to use this bot!",
                reply_markup=create_join_buttons()
            )
            return

        return handler_func(call)

    return wrapper

def get_db():
    return sqlite3.connect('telegram_bot.db')

def main_menu_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton(t(user_id, 'temp_mail')), types.KeyboardButton(t(user_id, 'temp_number')))
    markup.add(types.KeyboardButton(t(user_id, 'fake_address')), types.KeyboardButton(t(user_id, 'whatsapp_check')))
    markup.add(types.KeyboardButton(t(user_id, 'country_shortname')))
    markup.add(types.KeyboardButton(t(user_id, 'admin_support')))
    markup.add(types.KeyboardButton(t(user_id, 'language_change')))
    return markup

def language_selection_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"))
    markup.add(types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"))
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi"))
    markup.add(types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"))
    return markup

def admin_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("Number add"), types.KeyboardButton("Delete numbers"))
    markup.add(types.KeyboardButton("View all numbers"), types.KeyboardButton("Broadcast Message"))
    markup.add(types.KeyboardButton("Back to main menu"))
    return markup

def service_type_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Whatsapp number", callback_data="service_whatsapp"))
    markup.add(types.InlineKeyboardButton("Telegram number", callback_data="service_telegram"))
    markup.add(types.InlineKeyboardButton("Facebook number", callback_data="service_facebook"))
    return markup

def get_countries_for_service(service_type):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT country FROM numbers
        WHERE service_type = ? AND is_assigned = 0
    ''', (service_type,))
    countries = cursor.fetchall()
    conn.close()
    return [c[0] for c in countries]

def get_all_countries_for_service(service_type):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT country FROM numbers
        WHERE service_type = ?
    ''', (service_type,))
    countries = cursor.fetchall()
    conn.close()
    return [c[0] for c in countries]

def get_number_counts(service_type, country):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_assigned = 0 THEN 1 ELSE 0 END) as available,
            SUM(CASE WHEN is_assigned = 1 THEN 1 ELSE 0 END) as assigned
        FROM numbers
        WHERE service_type = ? AND country = ?
    ''', (service_type, country))
    result = cursor.fetchone()
    conn.close()
    return {
        'total': result[0] or 0,
        'available': result[1] or 0,
        'assigned': result[2] or 0
    }

def delete_numbers(service_type, country, delete_all=False):
    conn = get_db()
    cursor = conn.cursor()

    if delete_all:
        cursor.execute('''
            DELETE FROM user_assignments
            WHERE number_id IN (
                SELECT id FROM numbers
                WHERE service_type = ? AND country = ?
            )
        ''', (service_type, country))

        cursor.execute('''
            DELETE FROM numbers
            WHERE service_type = ? AND country = ?
        ''', (service_type, country))
    else:
        cursor.execute('''
            DELETE FROM numbers
            WHERE service_type = ? AND country = ? AND is_assigned = 0
        ''', (service_type, country))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def country_keyboard(service_type, exclude_number_id=None):
    markup = types.InlineKeyboardMarkup()
    countries = get_countries_for_service(service_type)

    for country in countries:
        if exclude_number_id:
            markup.add(types.InlineKeyboardButton(country, callback_data=f"country_{service_type}_{country}_{exclude_number_id}"))
        else:
            markup.add(types.InlineKeyboardButton(country, callback_data=f"country_{service_type}_{country}"))

    if not countries:
        markup.add(types.InlineKeyboardButton("❌ No numbers available", callback_data="no_numbers"))

    return markup

def assign_number_to_user(user_id, service_type, country, exclude_number_id=None):
    conn = get_db()
    cursor = conn.cursor()

    if exclude_number_id:
        cursor.execute('''
            SELECT id, phone_number FROM numbers
            WHERE service_type = ? AND country = ? AND is_assigned = 0 AND id != ?
            LIMIT 1
        ''', (service_type, country, exclude_number_id))
    else:
        cursor.execute('''
            SELECT id, phone_number FROM numbers
            WHERE service_type = ? AND country = ? AND is_assigned = 0
            LIMIT 1
        ''', (service_type, country))

    result = cursor.fetchone()

    if result:
        number_id, phone_number = result
        now = datetime.now().isoformat()

        cursor.execute('''
            UPDATE numbers
            SET is_assigned = 1, assigned_to = ?, assigned_at = ?
            WHERE id = ?
        ''', (user_id, now, number_id))

        cursor.execute('''
            INSERT INTO user_assignments (user_id, number_id, assigned_at)
            VALUES (?, ?, ?)
        ''', (user_id, number_id, now))

        conn.commit()
        conn.close()
        return phone_number, number_id

    conn.close()
    return None, None

def unassign_number(number_id):
    # This function is not fully implemented in the original code, it just 'pass'es.
    # It would typically involve setting is_assigned back to 0 or deleting the assignment.
    # Leaving it as is, based on the provided code structure.
    pass

def generate_temp_email(provider_key='mailtm_1'):
    import random
    import string
    try:
        provider = TEMP_MAIL_PROVIDERS.get(provider_key, TEMP_MAIL_PROVIDERS['mailtm_1'])
        api_base = provider['api_base']
        provider_type = provider.get('type', 'guerrilla')
        
        if provider_type == 'mailtm':
            available_domains = fetch_mailtm_domains()
            
            if not available_domains:
                print(f"No available domains for Mail.tm ({provider_key})")
                return None, None, None
            
            domain = random.choice(available_domains)
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            email = f"{username}@{domain}"
            
            account_data = {"address": email, "password": password}
            headers = {'Content-Type': 'application/json'}
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(f'{api_base}/accounts', json=account_data, headers=headers, timeout=15)
                    
                    if response.status_code == 201:
                        token_response = requests.post(f'{api_base}/token', json=account_data, headers=headers, timeout=15)
                        if token_response.status_code == 200:
                            token_data = token_response.json()
                            token = token_data.get('token')
                            if token:
                                print(f"Successfully created Mail.tm account: {email}")
                                return email, token, provider_key
                        else:
                            print(f"Token fetch failed (attempt {attempt+1}/{max_retries}): Status {token_response.status_code}")
                            if attempt < max_retries - 1:
                                username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                                email = f"{username}@{domain}"
                                account_data = {"address": email, "password": password}
                                time.sleep(1)
                                continue
                    elif response.status_code == 422:
                        print(f"Account creation failed (attempt {attempt+1}/{max_retries}): Domain/address issue, trying different domain and credentials")
                        if attempt < max_retries - 1:
                            if len(available_domains) > 1:
                                domain = random.choice([d for d in available_domains if d != domain])
                            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                            email = f"{username}@{domain}"
                            account_data = {"address": email, "password": password}
                            time.sleep(1)
                            continue
                    else:
                        print(f"Mail.tm API error (attempt {attempt+1}/{max_retries}): Status {response.status_code}, Response: {response.text[:200]}")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                            continue
                except requests.RequestException as req_error:
                    print(f"Network error creating Mail.tm account (attempt {attempt+1}/{max_retries}): {req_error}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                
                break
        
        elif provider_type == 'tempmail_plus':
            response = requests.post(f'{api_base}/inbox/create', timeout=15)
            if response.status_code == 200:
                data = response.json()
                email = data.get('email')
                inbox_id = data.get('id')
                if email and inbox_id:
                    return email, inbox_id, provider_key
        
        elif provider_type == 'tempmail_lol':
            response = requests.post(f'{api_base}/generate', timeout=15)
            if response.status_code == 200:
                data = response.json()
                email = data.get('address')
                token = data.get('token')
                if email and token:
                    return email, token, provider_key
        
        else:
            domain = provider.get('domain', 'guerrillamail.com')
            response = requests.get(f'{api_base}?f=get_email_address&domain={domain}', timeout=20)
            if response.status_code == 200:
                data = response.json()
                email = data.get('email_addr')
                token = data.get('sid_token')
                
                if email and '@' in email:
                    print(f"Successfully created Guerrilla email: {email}")
                    return email, token, provider_key
    except Exception as e:
        print(f"Error generating temp email ({provider_key}): {e}")
        import traceback
        traceback.print_exc()
    return None, None, None

def check_temp_email_inbox(sid_token, provider_key='mailtm_1'):
    try:
        provider = TEMP_MAIL_PROVIDERS.get(provider_key, TEMP_MAIL_PROVIDERS['mailtm_1'])
        api_base = provider['api_base']
        provider_type = provider.get('type', 'guerrilla')
        
        if provider_type == 'mailtm':
            headers = {'Authorization': f'Bearer {sid_token}'}
            response = requests.get(f'{api_base}/messages', headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                messages = data.get('hydra:member', [])
                return [{
                    'mail_id': msg.get('id'),
                    'mail_subject': msg.get('subject', 'No Subject'),
                    'mail_from': msg.get('from', {}).get('address', 'Unknown') if isinstance(msg.get('from'), dict) else str(msg.get('from', 'Unknown')),
                    'mail_date': msg.get('createdAt', '')
                } for msg in messages]
        
        elif provider_type == 'tempmail_plus':
            inbox_id = sid_token
            response = requests.get(f'{api_base}/mails?inbox_id={inbox_id}', timeout=15)
            if response.status_code == 200:
                data = response.json()
                mail_list = data.get('mail_list', [])
                return [{
                    'mail_id': msg.get('id'),
                    'mail_subject': msg.get('subject', 'No Subject'),
                    'mail_from': msg.get('from', 'Unknown'),
                    'mail_date': msg.get('time', '')
                } for msg in mail_list]
        
        elif provider_type == 'tempmail_lol':
            headers = {'Authorization': f'Bearer {sid_token}'}
            response = requests.get(f'{api_base}/inbox', headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                emails = data.get('email', [])
                return [{
                    'mail_id': msg.get('id'),
                    'mail_subject': msg.get('subject', 'No Subject'),
                    'mail_from': msg.get('from', 'Unknown'),
                    'mail_date': msg.get('date', '')
                } for msg in emails]
        
        else:
            response = requests.get(f'{api_base}?f=get_email_list&sid_token={sid_token}&offset=0', timeout=20)
            if response.status_code == 200:
                data = response.json()
                return data.get('list', [])
    except Exception as e:
        print(f"Error checking inbox ({provider_key}): {e}")
    return []

def read_temp_email_message(sid_token, msg_id, provider_key='mailtm_1'):
    try:
        provider = TEMP_MAIL_PROVIDERS.get(provider_key, TEMP_MAIL_PROVIDERS['mailtm_1'])
        api_base = provider['api_base']
        provider_type = provider.get('type', 'guerrilla')
        
        if provider_type == 'mailtm':
            headers = {'Authorization': f'Bearer {sid_token}'}
            response = requests.get(f'{api_base}/messages/{msg_id}', headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data:
                    mail_body = data.get('html', []) or data.get('text', '') or 'No content'
                    if isinstance(mail_body, list) and len(mail_body) > 0:
                        mail_body = mail_body[0]
                    return {'mail_body': mail_body}, None
                return None, "Empty message"
            else:
                print(f"Mail.tm API Error: Status {response.status_code}")
                return None, f"API error {response.status_code}"
        
        elif provider_type == 'tempmail_plus':
            inbox_id = sid_token
            response = requests.get(f'{api_base}/mails/{msg_id}?inbox_id={inbox_id}', timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data:
                    mail_body = data.get('html', '') or data.get('text', '') or 'No content'
                    return {'mail_body': mail_body}, None
                return None, "Empty message"
            else:
                return None, f"API error {response.status_code}"
        
        elif provider_type == 'tempmail_lol':
            headers = {'Authorization': f'Bearer {sid_token}'}
            response = requests.get(f'{api_base}/read/{msg_id}', headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data:
                    mail_body = data.get('html', '') or data.get('body', '') or 'No content'
                    return {'mail_body': mail_body}, None
                return None, "Empty message"
            else:
                return None, f"API error {response.status_code}"
        
        else:
            response = requests.get(f'{api_base}?f=fetch_email&sid_token={sid_token}&email_id={msg_id}', timeout=20)
            if response.status_code == 200:
                return response.json(), None
            else:
                print(f"Guerrilla API Error: Status {response.status_code}")
                return None, f"API error {response.status_code}"
    except requests.RequestException as e:
        print(f"Network error fetching email ({provider_key}): {e}")
        return None, "Network error"
    except Exception as e:
        print(f"Error reading email message ({provider_key}): {e}")
        return None, "Processing error"
    return None, "Unknown error"

def clean_html_content(html_content):
    """Extract plain text and links from HTML email content"""
    if not html_content:
        return 'No content', []
    
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for tag in soup(['style', 'script', 'head', 'meta', 'link']):
        tag.decompose()
    
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag.get('href', '')
        
        if isinstance(href, (list, tuple)):
            href = href[0] if href else ''
        
        if href and isinstance(href, str) and (href.startswith('http://') or href.startswith('https://')):
            links.append(href)
    
    text = soup.get_text(separator='\n', strip=True)
    text = re.sub(r'\n\s*\n+', '\n\n', text).strip()
    
    return (text if text else 'No content', links)

def generate_custom_phone_number(country_code_lower):
    import random
    
    custom_formats = {
        'pakistan': lambda: f"+92-{random.choice(['300', '301', '302', '321', '333', '345'])}-{random.randint(1000000, 9999999)}"
    }
    
    if country_code_lower in custom_formats:
        return custom_formats[country_code_lower]()
    return None

def generate_fake_address(country_name='US'):
    try:
        import random
        
        major_cities = {
            'bangladesh': ['Dhaka', 'Chittagong', 'Khulna', 'Rajshahi', 'Sylhet'],
            'usa': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
            'united states': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
            'uk': ['London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow'],
            'united kingdom': ['London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow'],
            'india': ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata'],
            'germany': ['Berlin', 'Hamburg', 'Munich', 'Cologne', 'Frankfurt'],
            'france': ['Paris', 'Marseille', 'Lyon', 'Toulouse', 'Nice'],
            'spain': ['Madrid', 'Barcelona', 'Valencia', 'Seville', 'Bilbao'],
            'italy': ['Rome', 'Milan', 'Naples', 'Turin', 'Florence'],
            'canada': ['Toronto', 'Montreal', 'Vancouver', 'Calgary', 'Ottawa'],
            'australia': ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide'],
            'brazil': ['São Paulo', 'Rio de Janeiro', 'Brasília', 'Salvador', 'Fortaleza'],
            'pakistan': ['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad'],
            'china': ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen', 'Chengdu'],
            'japan': ['Tokyo', 'Osaka', 'Yokohama', 'Nagoya', 'Sapporo'],
            'mexico': ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana'],
            'russia': ['Moscow', 'Saint Petersburg', 'Novosibirsk', 'Yekaterinburg', 'Kazan'],
            'turkey': ['Istanbul', 'Ankara', 'Izmir', 'Bursa', 'Antalya'],
            'denmark': ['Copenhagen', 'Aarhus', 'Odense', 'Aalborg', 'Esbjerg'],
            'finland': ['Helsinki', 'Espoo', 'Tampere', 'Vantaa', 'Oulu'],
            'ireland': ['Dublin', 'Cork', 'Limerick', 'Galway', 'Waterford'],
            'iran': ['Tehran', 'Mashhad', 'Isfahan', 'Karaj', 'Shiraz'],
            'netherlands': ['Amsterdam', 'Rotterdam', 'The Hague', 'Utrecht', 'Eindhoven'],
            'new zealand': ['Auckland', 'Wellington', 'Christchurch', 'Hamilton', 'Dunedin'],
            'norway': ['Oslo', 'Bergen', 'Stavanger', 'Trondheim', 'Drammen'],
            'switzerland': ['Zurich', 'Geneva', 'Basel', 'Lausanne', 'Bern']
        }
        
        country_locales = {
            'bangladesh': 'bn_BD',
            'usa': 'en_US',
            'united states': 'en_US',
            'uk': 'en_GB',
            'united kingdom': 'en_GB',
            'india': 'en_IN',
            'germany': 'de_DE',
            'france': 'fr_FR',
            'spain': 'es_ES',
            'italy': 'it_IT',
            'canada': 'en_CA',
            'australia': 'en_AU',
            'brazil': 'pt_BR',
            'pakistan': 'custom',
            'china': 'zh_CN',
            'japan': 'ja_JP',
            'mexico': 'es_MX',
            'russia': 'ru_RU',
            'turkey': 'tr_TR',
            'denmark': 'da_DK',
            'finland': 'fi_FI',
            'ireland': 'en_IE',
            'iran': 'fa_IR',
            'netherlands': 'nl_NL',
            'new zealand': 'en_NZ',
            'norway': 'no_NO',
            'switzerland': 'de_CH'
        }
        
        country_short_codes = {
            'bangladesh': 'BD',
            'usa': 'US',
            'united states': 'US',
            'uk': 'GB',
            'united kingdom': 'GB',
            'india': 'IN',
            'germany': 'DE',
            'france': 'FR',
            'spain': 'ES',
            'italy': 'IT',
            'canada': 'CA',
            'australia': 'AU',
            'brazil': 'BR',
            'pakistan': 'PK',
            'china': 'CN',
            'japan': 'JP',
            'mexico': 'MX',
            'russia': 'RU',
            'turkey': 'TR',
            'denmark': 'DK',
            'finland': 'FI',
            'ireland': 'IE',
            'iran': 'IR',
            'netherlands': 'NL',
            'new zealand': 'NZ',
            'norway': 'NO',
            'switzerland': 'CH'
        }
        
        cities = major_cities.get(country_name.lower(), ['Capital City'])
        selected_city = random.choice(cities)
        
        headers = {
            'User-Agent': 'TelegramBot/1.0'
        }
        
        search_url = f'https://nominatim.openstreetmap.org/search?city={selected_city}&format=json&addressdetails=1&limit=20'
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                place = random.choice(results)
                address = place.get('address', {})
                
                road = address.get('road', address.get('street', address.get('pedestrian', '')))
                house_number = address.get('house_number', random.randint(1, 999))
                
                if road:
                    street_address = f"{house_number} {road}".strip()
                else:
                    street_names = ['Main Street', 'High Street', 'Park Avenue', 'Market Road', 'Station Road']
                    street_address = f"{house_number} {random.choice(street_names)}"
                
                city = address.get('city', address.get('town', address.get('village', selected_city)))
                state = address.get('state', address.get('province', address.get('region', address.get('county', 'N/A'))))
                zipcode = address.get('postcode', random.randint(10000, 99999))
                country = address.get('country', country_name.title())
                
                locale = country_locales.get(country_name.lower(), 'en_US')
                country_code = country_short_codes.get(country_name.lower(), 'US')
                
                if locale == 'custom':
                    custom_phone = generate_custom_phone_number(country_name.lower())
                    phone = custom_phone if custom_phone else '+00-000-0000000'
                    fake = Faker('en_US')
                    full_name = fake.name()
                else:
                    fake = Faker(locale)
                    full_name = fake.name()
                    phone = fake.phone_number()
                
                address_data = {
                    'name': full_name,
                    'street': street_address,
                    'city': city,
                    'state': state,
                    'zipcode': str(zipcode),
                    'country': country,
                    'phone': phone,
                    'country_code': country_code
                }
                
                return address_data
        
        return None
    except Exception as e:
        return None

def get_user_current_number(user_id, service_type):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT n.id, n.phone_number, n.country
        FROM numbers n
        JOIN user_assignments ua ON n.id = ua.number_id
        WHERE ua.user_id = ? AND n.service_type = ? AND n.is_assigned = 1
        ORDER BY ua.assigned_at DESC
        LIMIT 1
    ''', (user_id, service_type))
    result = cursor.fetchone()
    conn.close()
    return result

def format_phone_number(phone_number, default_country='BD'):
    try:
        clean_number = re.sub(r'[^\d+]', '', phone_number)

        if clean_number.startswith('0') and len(clean_number) == 11:
            clean_number = '+880' + clean_number[1:]
        elif not clean_number.startswith('+'):
            clean_number = '+' + clean_number

        try:
            parsed = phonenumbers.parse(clean_number, None)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            pass

        return clean_number
    except:
        return None

def check_whatsapp_number(phone_number):
    try:
        formatted_number = format_phone_number(phone_number)

        if not formatted_number:
            return {'status': 'invalid', 'has_whatsapp': False, 'is_business': False, 'error': 'Invalid phone number format'}

        if not MAYTAPI_PRODUCT_ID or not MAYTAPI_PHONE_ID or not MAYTAPI_TOKEN:
            # Modified to use the directly assigned variables
            try:
                parsed = phonenumbers.parse(formatted_number, None)
                if phonenumbers.is_valid_number(parsed):
                    return {'status': 'valid_format', 'has_whatsapp': None, 'is_business': None, 'error': 'Maytapi API not configured'}
                else:
                    return {'status': 'invalid', 'has_whatsapp': False, 'is_business': False, 'error': 'Invalid number'}
            except:
                return {'status': 'invalid', 'has_whatsapp': False, 'is_business': False, 'error': 'Parse error'}

        clean_number = formatted_number.replace('+', '')
        whatsapp_number = f"{clean_number}@c.us"

        # Using the directly assigned variables
        url = f"https://api.maytapi.com/api/{MAYTAPI_PRODUCT_ID}/{MAYTAPI_PHONE_ID}/checkNumberStatus"
        headers = {
            'x-maytapi-key': MAYTAPI_TOKEN
        }
        params = {
            'token': MAYTAPI_TOKEN,
            'number': whatsapp_number
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                result = data.get('result', {})
                status_code = result.get('status', 0)
                is_business = result.get('isBusiness', False)
                can_receive = result.get('canReceiveMessage', False)

                if status_code == 200:
                    return {
                        'status': 'registered',
                        'has_whatsapp': True,
                        'is_business': is_business,
                        'can_receive': can_receive,
                        'number': formatted_number
                    }
                elif status_code == 404:
                    return {
                        'status': 'not_registered',
                        'has_whatsapp': False,
                        'is_business': False,
                        'can_receive': False,
                        'number': formatted_number
                    }
                else:
                    return {
                        'status': 'unknown_status',
                        'has_whatsapp': False,
                        'is_business': False,
                        'can_receive': False,
                        'number': formatted_number,
                        'error': f'Unknown status code: {status_code}'
                    }
            else:
                return {'status': 'api_error', 'has_whatsapp': False, 'is_business': False, 'error': data.get('message', 'Unknown error')}
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', error_data.get('error', f'HTTP {response.status_code}'))
            except:
                error_msg = f'HTTP {response.status_code}'

            return {'status': 'api_error', 'has_whatsapp': False, 'is_business': False, 'error': error_msg}

    except requests.exceptions.Timeout:
        return {'status': 'timeout', 'has_whatsapp': False, 'is_business': False, 'error': 'Request timeout'}
    except Exception as e:
        return {'status': 'error', 'has_whatsapp': False, 'is_business': False, 'error': str(e)}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id

    if not is_user_member(user_id):
        not_joined = check_user_membership(user_id)

        channel_names = ', '.join([ch['name'] for ch in not_joined])

        bot.send_message(
            user_id,
            f"🔔 Welcome to the Bot!\n\n"
            f"আমাদের বট ব্যবহার করার জন্য আপনাকে নিচের সব channel/group এ join করতে হবে।\n\n"
            f"To use this bot, you must join all our channels/groups.\n\n"
            f"👇 Please join all channels below:",
            reply_markup=create_join_buttons()
        )
        return

    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    is_new, user_count = register_user(user_id, username, first_name, last_name)
    
    if is_new and user_id != ADMIN_CHAT_ID:
        try:
            bot.send_message(
                ADMIN_CHAT_ID,
                f"🔔 New User Registered!\n\n"
                f"👤 User #{user_count}\n"
                f"📝 Username: @{username if username else 'No username'}\n"
                f"👤 Name: {first_name} {last_name}\n"
                f"🆔 User ID: {user_id}"
            )
        except:
            pass

    if user_id == ADMIN_CHAT_ID:
        bot.send_message(
            user_id,
            "🔐 Admin Panel - Welcome!\n\nChoose an option:",
            reply_markup=admin_menu_keyboard()
        )
    else:
        if is_new:
            bot.send_message(
                user_id,
                "🌍 Welcome! / স্বাগতম! / Добро пожаловать! / स्वागत है! / مرحبا!\n\nPlease select your language:\nঅনুগ্রহ করে আপনার ভাষা নির্বাচন করুন:",
                reply_markup=language_selection_keyboard()
            )
        else:
            bot.send_message(
                user_id,
                t(user_id, 'welcome'),
                reply_markup=main_menu_keyboard(user_id)
            )

@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def handle_check_membership(call):
    user_id = call.message.chat.id

    if is_user_member(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)

        username = call.from_user.username or ""
        first_name = call.from_user.first_name or ""
        last_name = call.from_user.last_name or ""
        
        is_new, user_count = register_user(user_id, username, first_name, last_name)
        
        if is_new and user_id != ADMIN_CHAT_ID:
            try:
                bot.send_message(
                    ADMIN_CHAT_ID,
                    f"🔔 New User Registered!\n\n"
                    f"👤 User #{user_count}\n"
                    f"📝 Username: @{username if username else 'No username'}\n"
                    f"👤 Name: {first_name} {last_name}\n"
                    f"🆔 User ID: {user_id}"
                )
            except:
                pass

        if user_id == ADMIN_CHAT_ID:
            bot.send_message(
                user_id,
                "🔐 Admin Panel - Welcome!\n\nChoose an option:",
                reply_markup=admin_menu_keyboard()
            )
        else:
            bot.send_message(
                user_id,
                "🌍 Welcome! / স্বাগতম! / Добро пожаловать! / स्वागत है! / مرحبا!\n\nPlease select your language:\nঅনুগ্রহ করে আপনার ভাষা নির্বাচন করুন:",
                reply_markup=language_selection_keyboard()
            )
    else:
        not_joined = check_user_membership(user_id)
        channel_names = ', '.join([ch['name'] for ch in not_joined])

        bot.answer_callback_query(
            call.id,
            f"❌ You haven't joined all channels yet!\n\nPlease join: {channel_names}",
            show_alert=True
        )

@bot.message_handler(func=lambda message: message.text in [t(message.chat.id, 'temp_number'), "📱 Temp number"])
@require_membership
def temp_number_menu(message):
    bot.send_message(
        message.chat.id,
        "Select service type:",
        reply_markup=service_type_keyboard()
    )

@bot.message_handler(func=lambda message: message.text in [t(message.chat.id, 'fake_address'), "🏠 Fake address"])
@require_membership
def fake_address_start(message):
    user_id = message.chat.id
    user_fake_address_state[user_id] = True
    bot.send_message(
        user_id,
        "🌍 Enter country name:\n\n"
        "Examples: Bangladesh, USA, UK, India, Germany, France, Spain, Italy, Canada, Australia, Brazil, Denmark, Finland, Ireland, Iran, Mexico, Netherlands, New Zealand, Norway, Switzerland, Turkey"
    )

def process_fake_address(message):
    country = message.text.strip()
    address = generate_fake_address(country)

    if address:
        response = f"🏠 Fake Address Generated!\n\n"
        response += f"👤 Name: {address['name']}\n"
        response += f"🏡 Street: {address['street']}\n"
        response += f"🏙 City: {address['city']}\n"
        response += f"📍 State: {address['state']}\n"
        response += f"📮 Zipcode: {address['zipcode']}\n"
        response += f"🌍 Country: {address['country']}\n"
        response += f"📱 Phone: {address['phone']}\n"
        response += f"🏳️ Country Code: {address.get('country_code', 'N/A')}"

        bot.send_message(message.chat.id, response, reply_markup=main_menu_keyboard(message.chat.id))
    else:
        bot.send_message(
            message.chat.id,
            "❌ Failed to generate address. Try again.",
            reply_markup=main_menu_keyboard(message.chat.id)
        )

@bot.message_handler(func=lambda message: message.text in [t(message.chat.id, 'country_shortname'), "🌍 Country Short name"])
@require_membership
def country_shortname_start(message):
    user_id = message.chat.id
    user_country_lookup_state[user_id] = True
    bot.send_message(
        user_id,
        "🌍 Country Short Name Finder\n\n"
        "দেশের নাম লিখে পাঠান / Send your country name:\n\n"
        "উদাহরণ / Examples:\n"
        "• Bangladesh\n"
        "• United States\n"
        "• India\n"
        "• United Kingdom\n"
        "• Pakistan"
    )

def process_country_lookup(message):
    country_input = message.text.strip()
    user_id = message.chat.id
    
    found_countries = []
    for country_name, codes in COUNTRY_DATA.items():
        if country_input.lower() in country_name.lower():
            found_countries.append((country_name, codes))
    
    if not found_countries:
        bot.send_message(
            user_id,
            f"❌ দেশ পাওয়া যায়নি / Country not found: {country_input}\n\n"
            "অনুগ্রহ করে সঠিক দেশের নাম লিখুন।\n"
            "Please enter the correct country name.",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    if len(found_countries) == 1:
        country_name, codes = found_countries[0]
        response = f"🌍 Country Short Name / দেশের সংক্ষিপ্ত নাম\n\n"
        response += f"📍 দেশ / Country: {country_name}\n\n"
        response += f"🔤 Alpha-2 Code: `{codes['alpha2']}`\n"
        response += f"🔤 Alpha-3 Code: `{codes['alpha3']}`\n"
        response += f"🔢 Numeric Code: `{codes['numeric']}`\n\n"
        response += f"✅ Tap to copy!"
        
        bot.send_message(
            user_id,
            response,
            reply_markup=main_menu_keyboard(user_id),
            parse_mode='Markdown'
        )
    else:
        markup = types.InlineKeyboardMarkup()
        response = f"🔍 একাধিক দেশ পাওয়া গেছে / Multiple countries found:\n\n"
        
        for country_name, codes in found_countries[:10]:
            response += f"• {country_name}\n"
            markup.add(types.InlineKeyboardButton(
                country_name,
                callback_data=f"countrycode_{country_name[:30]}"
            ))
        
        response += "\nনিচের বাটন থেকে নির্বাচন করুন:\nSelect from buttons below:"
        
        bot.send_message(
            user_id,
            response,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('countrycode_'))
@require_membership_callback
def country_code_selection(call):
    country_prefix = call.data.replace('countrycode_', '')
    user_id = call.message.chat.id
    
    for country_name, codes in COUNTRY_DATA.items():
        if country_name.startswith(country_prefix):
            response = f"🌍 Country Short Name / দেশের সংক্ষিপ্ত নাম\n\n"
            response += f"📍 দেশ / Country: {country_name}\n\n"
            response += f"🔤 Alpha-2 Code: `{codes['alpha2']}`\n"
            response += f"🔤 Alpha-3 Code: `{codes['alpha3']}`\n"
            response += f"🔢 Numeric Code: `{codes['numeric']}`\n\n"
            response += f"✅ Tap to copy!"
            
            bot.edit_message_text(
                response,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "✅ Country codes found!")
            return
    
    bot.answer_callback_query(call.id, "❌ Country not found!", show_alert=True)

@bot.message_handler(func=lambda message: message.text in [t(message.chat.id, 'temp_mail'), "📧 Temp mail"])
@require_membership
def temp_mail_menu(message):
    markup = types.InlineKeyboardMarkup()
    current_email = user_temp_emails.get(message.chat.id)

    if current_email:
        provider_key = user_selected_provider.get(message.chat.id, 'guerrilla_com')
        provider = TEMP_MAIL_PROVIDERS[provider_key]
        markup.add(types.InlineKeyboardButton("📬 Inbox", callback_data="tempmail_inbox"))
        markup.add(types.InlineKeyboardButton("🔄 Change Mail", callback_data="tempmail_show_providers"))
        markup.add(types.InlineKeyboardButton("🗑 Delete Mail", callback_data="tempmail_delete"))
        text = f"📧 Your Current Temp Mail:\n\n✉️ Email: {current_email}\n\n🌐 Provider: {provider['name']}\n\nTap to copy!"
    else:
        markup.add(types.InlineKeyboardButton("📧 Get Mail", callback_data="tempmail_show_providers"))
        text = "📧 Temp Mail Service\n\nClick 'Get Mail' to select a provider and generate email:"

    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [t(message.chat.id, 'whatsapp_check'), "✅ Whatsapp Chak", "✅ Whatsapp Check"])
@require_membership
def whatsapp_check_start(message):
    user_id = message.chat.id
    msg = bot.send_message(
        user_id,
        t(user_id, 'whatsapp_checker_title') + '\n\n' + t(user_id, 'whatsapp_checker_desc')
    )
    bot.register_next_step_handler(msg, process_whatsapp_check)

def process_whatsapp_check(message):
    input_text = message.text.strip()
    user_id = message.chat.id

    pattern = r'\+?[\d]{10,15}'
    found_numbers = re.findall(pattern, input_text)

    if not found_numbers:
        bot.send_message(
            user_id,
            t(user_id, 'no_numbers_found'),
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    total_numbers = len(found_numbers)

    progress_msg = bot.send_message(
        user_id,
        f"✅ {t(user_id, 'checking_progress')} {total_numbers} {t(user_id, 'checking_wait')}"
    )

    whatsapp_personal = []
    whatsapp_business = []
    whatsapp_not_available = []
    invalid_numbers = []
    api_errors = []

    for idx, number in enumerate(found_numbers, 1):
        clean_number = number if number.startswith('+') else '+' + number

        if idx % 5 == 0:
            bot.edit_message_text(
                f"✅ {t(user_id, 'checking_progress')} {total_numbers} {t(user_id, 'checking_wait')}\n\n{t(user_id, 'checking_status')} {idx}/{total_numbers}...",
                user_id,
                progress_msg.message_id
            )

        result = check_whatsapp_number(clean_number)

        if result['has_whatsapp']:
            number_info = {
                'number': result.get('number', clean_number),
                'is_business': result['is_business']
            }
            if result['is_business']:
                whatsapp_business.append(number_info)
            else:
                whatsapp_personal.append(number_info)
        elif result['status'] in ['not_registered', 'registered']:
            whatsapp_not_available.append(clean_number)
        elif result['status'] in ['invalid']:
            invalid_numbers.append(clean_number)
        else:
            api_errors.append({'number': clean_number, 'error': result.get('error', 'Unknown')})

        time.sleep(0.5)

    bot.delete_message(user_id, progress_msg.message_id)

    response_text = f"{t(user_id, 'whatsapp_results')} {total_numbers}\n"
    response_text += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    if whatsapp_personal:
        response_text += f"{t(user_id, 'whatsapp_personal_list')} ({len(whatsapp_personal)}):\n"
        for info in whatsapp_personal:
            response_text += f"📱 `{info['number']}`\n"
        response_text += "\n"

    if whatsapp_business:
        response_text += f"{t(user_id, 'whatsapp_business_list')} ({len(whatsapp_business)}):\n"
        for info in whatsapp_business:
            response_text += f"🏢 `{info['number']}`\n"
        response_text += "\n"

    if whatsapp_not_available:
        response_text += f"{t(user_id, 'no_whatsapp_list')} ({len(whatsapp_not_available)}):\n"
        for num in whatsapp_not_available:
            response_text += f"📵 `{num}`\n"
        response_text += "\n"

    if invalid_numbers:
        response_text += f"{t(user_id, 'invalid_numbers_list')} ({len(invalid_numbers)}):\n"
        for num in invalid_numbers:
            response_text += f"❌ `{num}`\n"
        response_text += "\n"

    if api_errors:
        response_text += f"{t(user_id, 'api_errors_list')} ({len(api_errors)}):\n"
        for item in api_errors[:5]:
            response_text += f"⚡ `{item['number']}` - {item['error']}\n"
        response_text += "\n"

    response_text += "━━━━━━━━━━━━━━━━━━━━\n"
    response_text += t(user_id, 'powered_by')

    if len(response_text) > 4000:
        response_text = response_text[:4000] + "\n\n... (truncated)"

    bot.send_message(
        user_id,
        response_text,
        reply_markup=main_menu_keyboard(user_id),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text in [t(message.chat.id, 'admin_support'), "Admin support"])
@require_membership
def admin_support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Contact Admin", url="https://t.me/OwnerOf_Xion_Crypto"))
    
    bot.send_message(
        message.chat.id,
        "👨‍💼 Admin Support\n\n"
        "যদি কোন সমস্যা হয় বা সাহায্য প্রয়োজন হয়, নিচের বাটনে ক্লিক করুন:\n\n"
        "If you need help or have any issues, click the button below:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "Number add")
def number_add_start(message):
    if message.chat.id == ADMIN_CHAT_ID:
        msg = bot.send_message(message.chat.id, "Select service type for the new number:")
        bot.register_next_step_handler(msg, process_service_type_admin)
    else:
        bot.send_message(message.chat.id, "Unauthorized access.")

def process_service_type_admin(message):
    service_types = {
        '1': 'whatsapp',
        '2': 'telegram',
        '3': 'facebook',
        'whatsapp': 'whatsapp',
        'telegram': 'telegram',
        'facebook': 'facebook'
    }

    service_type = service_types.get(message.text.lower())

    if not service_type:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Whatsapp", callback_data="admin_add_whatsapp"))
        markup.add(types.InlineKeyboardButton("Telegram", callback_data="admin_add_telegram"))
        markup.add(types.InlineKeyboardButton("Facebook", callback_data="admin_add_facebook"))
        bot.send_message(message.chat.id, "Please select service type:", reply_markup=markup)
        return

    admin_state[message.chat.id] = {'step': 'country', 'service_type': service_type}
    msg = bot.send_message(message.chat.id, "Enter country name:")
    bot.register_next_step_handler(msg, process_country_admin)

def process_country_admin(message):
    if message.chat.id not in admin_state:
        bot.send_message(message.chat.id, "Session expired. Please start again.")
        return

    admin_state[message.chat.id]['country'] = message.text
    admin_state[message.chat.id]['step'] = 'number'

    msg = bot.send_message(
        message.chat.id,
        f"📱 Enter phone numbers for {message.text}:\n\n"
        f"Single number: +8801427530945\n"
        f"Or multiple (up to 500):\n"
        f"+8801427530945)\n"
        f"+8801427536660)\n"
        f"+8801427535519)\n\n"
        f"Each number starts with +\n"
        f"Closing ) is optional"
    )
    bot.register_next_step_handler(msg, process_number_admin)

def process_number_admin(message):
    if message.chat.id not in admin_state:
        bot.send_message(message.chat.id, "Session expired. Please start again.")
        return

    state = admin_state[message.chat.id]
    country = state['country']
    service_type = state['service_type']

    input_text = message.text
    pattern = r'\+[^\s)]+\)?'

    found_numbers = re.findall(pattern, input_text)

    if not found_numbers:
        bot.send_message(
            message.chat.id,
            "❌ No valid numbers found!\n\n"
            "Please use the format:\n"
            "+8801427530945)\n"
            "+8801427536660)\n\n"
            "Try again:",
            reply_markup=admin_menu_keyboard()
        )
        if message.chat.id in admin_state:
            del admin_state[message.chat.id]
        return

    if len(found_numbers) > 500:
        bot.send_message(
            message.chat.id,
            f"⚠️ Too many numbers!\n\n"
            f"You provided {len(found_numbers)} numbers.\n"
            f"Maximum allowed is 500 numbers per batch.\n"
            f"Please split your numbers into smaller batches.",
            reply_markup=admin_menu_keyboard()
        )
        if message.chat.id in admin_state:
            del admin_state[message.chat.id]
        return

    phone_numbers = [num.rstrip(')') for num in found_numbers]

    conn = get_db()
    cursor = conn.cursor()

    added_count = 0
    duplicate_count = 0
    other_error_count = 0
    duplicate_numbers = []
    failed_numbers = []

    for phone_number in phone_numbers:
        try:
            cursor.execute('''
                INSERT INTO numbers (country, phone_number, service_type)
                VALUES (?, ?, ?)
            ''', (country, phone_number, service_type))
            conn.commit()
            added_count += 1
        except sqlite3.IntegrityError:
            duplicate_count += 1
            duplicate_numbers.append(phone_number)
        except Exception as e:
            other_error_count += 1
            failed_numbers.append(phone_number)

    conn.close()

    result_message = f"📊 Bulk Number Addition Complete!\n\n"
    result_message += f"Country: {country}\n"
    result_message += f"Service: {service_type}\n\n"
    result_message += f"✅ Successfully added: {added_count} numbers\n"

    if duplicate_count > 0:
        result_message += f"⚠️ Duplicates (skipped): {duplicate_count} numbers\n"

    if other_error_count > 0:
        result_message += f"❌ Other errors: {other_error_count} numbers\n"

    result_message += f"\n📱 Total numbers processed: {len(phone_numbers)}"

    if duplicate_numbers and len(duplicate_numbers) <= 5:
        result_message += f"\n\n⚠️ Duplicate numbers (first 5):\n"
        for num in duplicate_numbers[:5]:
            result_message += f"{num}\n"

    if failed_numbers and len(failed_numbers) <= 5:
        result_message += f"\n\n❌ Failed numbers (first 5):\n"
        for num in failed_numbers[:5]:
            result_message += f"{num}\n"

    bot.send_message(
        message.chat.id,
        result_message,
        reply_markup=admin_menu_keyboard()
    )

    if message.chat.id in admin_state:
        del admin_state[message.chat.id]

@bot.message_handler(func=lambda message: message.text == "Delete numbers")
def delete_numbers_menu(message):
    if message.chat.id == ADMIN_CHAT_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Whatsapp", callback_data="delservice_whatsapp"))
        markup.add(types.InlineKeyboardButton("Telegram", callback_data="delservice_telegram"))
        markup.add(types.InlineKeyboardButton("Facebook", callback_data="delservice_facebook"))
        bot.send_message(message.chat.id, "Select service type to delete:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Unauthorized access.")

@bot.message_handler(func=lambda message: message.text == "View all numbers")
def view_all_numbers(message):
    if message.chat.id == ADMIN_CHAT_ID:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT country, phone_number, service_type, is_assigned FROM numbers')
        numbers = cursor.fetchall()
        conn.close()

        if numbers:
            text = "📊 All Numbers:\n\n"
            for country, phone, service, assigned in numbers:
                status = "🔴 Assigned" if assigned else "🟢 Available"
                text += f"{status} | {country} | {phone} | {service}\n"
            bot.send_message(message.chat.id, text)
        else:
            bot.send_message(message.chat.id, "No numbers in database.")
    else:
        bot.send_message(message.chat.id, "Unauthorized access.")

@bot.message_handler(func=lambda message: message.text == "Broadcast Message")
def broadcast_message_start(message):
    if message.chat.id == ADMIN_CHAT_ID:
        msg = bot.send_message(
            message.chat.id,
            "📢 Broadcast Message to All Users\n\n"
            "যে মেসেজটি সব ইউজারের কাছে পাঠাতে চান সেটি লিখুন:\n\n"
            "Write the message you want to send to all users:"
        )
        bot.register_next_step_handler(msg, process_broadcast_message)
    else:
        bot.send_message(message.chat.id, "Unauthorized access.")

def process_broadcast_message(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.send_message(message.chat.id, "Unauthorized access.")
        return
    
    broadcast_text = message.text
    all_users = get_all_user_ids()
    
    if not all_users:
        bot.send_message(
            message.chat.id,
            "❌ No users found in database.",
            reply_markup=admin_menu_keyboard()
        )
        return
    
    success_count = 0
    failed_count = 0
    
    progress_msg = bot.send_message(
        message.chat.id,
        f"📤 Sending broadcast to {len(all_users)} users...\n\nPlease wait..."
    )
    
    for user_id in all_users:
        if user_id == ADMIN_CHAT_ID:
            continue
        
        try:
            bot.send_message(user_id, f"📢 Admin Message:\n\n{broadcast_text}")
            success_count += 1
        except:
            failed_count += 1
        
        time.sleep(0.05)
    
    bot.delete_message(message.chat.id, progress_msg.message_id)
    
    bot.send_message(
        message.chat.id,
        f"✅ Broadcast Complete!\n\n"
        f"📊 Total Users: {len(all_users)}\n"
        f"✅ Sent Successfully: {success_count}\n"
        f"❌ Failed: {failed_count}",
        reply_markup=admin_menu_keyboard()
    )

@bot.message_handler(func=lambda message: message.text in [t(message.chat.id, 'language_change'), "🌐 ভাষা পরিবর্তন", "🌐 Language Change"])
@require_membership
def language_change_handler(message):
    bot.send_message(
        message.chat.id,
        t(message.chat.id, 'select_language'),
        reply_markup=language_selection_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    language_code = call.data.replace('lang_', '')
    user_id = call.message.chat.id
    
    set_user_language(user_id, language_code)
    
    bot.answer_callback_query(call.id, "✅ Language updated!")
    
    bot.edit_message_text(
        t(user_id, 'language_changed'),
        call.message.chat.id,
        call.message.message_id
    )
    
    bot.send_message(
        user_id,
        t(user_id, 'welcome'),
        reply_markup=main_menu_keyboard(user_id)
    )

@bot.message_handler(func=lambda message: message.text == "Back to main menu")
def back_to_main(message):
    bot.send_message(
        message.chat.id,
        "Main Menu:",
        reply_markup=main_menu_keyboard(message.chat.id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('service_'))
@require_membership_callback
def service_selection(call):
    service_type = call.data.split('_')[1]

    bot.edit_message_text(
        f"Select country for {service_type}:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=country_keyboard(service_type)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('country_'))
@require_membership_callback
def country_selection(call):
    parts = call.data.split('_')
    service_type = parts[1]

    exclude_number_id = None
    if len(parts) > 3 and parts[-1].isdigit():
        exclude_number_id = int(parts[-1])
        country = '_'.join(parts[2:-1])
    else:
        country = '_'.join(parts[2:])

    phone_number, number_id = assign_number_to_user(call.message.chat.id, service_type, country, exclude_number_id)

    if phone_number:
        text = f"📞 Your Number is Ready!\n\nTap to copy: `{phone_number}`\n\n✅ Your number is active!\n\n❗️Go to our OTP Group to see your incoming SMS."

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Change number", callback_data=f"change_{service_type}_{number_id}"))
        markup.add(types.InlineKeyboardButton("OTP", url=OTP_GROUP_LINK))

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "❌ No numbers available for this country.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('change_'))
@require_membership_callback
def change_number(call):
    parts = call.data.split('_')
    service_type = parts[1]
    old_number_id = int(parts[2])

    unassign_number(old_number_id)

    bot.edit_message_text(
        f"Select new country for {service_type}:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=country_keyboard(service_type, exclude_number_id=old_number_id)
    )

    bot.answer_callback_query(call.id, "Selecting new number. Previous number is retired permanently.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_'))
def admin_add_service(call):
    service_type = call.data.split('_')[2]
    admin_state[call.message.chat.id] = {'step': 'country', 'service_type': service_type}

    bot.edit_message_text(
        f"Enter country name for {service_type}:",
        call.message.chat.id,
        call.message.message_id
    )
    bot.register_next_step_handler(call.message, process_country_admin)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delservice_'))
def delete_service_selection(call):
    service_type = call.data.split('_')[1]
    countries = get_all_countries_for_service(service_type)

    if not countries:
        bot.edit_message_text(
            f"❌ No numbers found for {service_type}.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    markup = types.InlineKeyboardMarkup()
    for country in countries:
        markup.add(types.InlineKeyboardButton(
            country,
            callback_data=f"delcountry_{service_type}_{country}"
        ))

    bot.edit_message_text(
        f"Select country to delete from {service_type}:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delcountry_'))
def delete_country_selection(call):
    parts = call.data.split('_')
    service_type = parts[1]
    country = '_'.join(parts[2:])

    counts = get_number_counts(service_type, country)

    text = f"📊 Numbers for {country} ({service_type}):\n\n"
    text += f"Total: {counts['total']}\n"
    text += f"🟢 Available: {counts['available']}\n"
    text += f"🔴 Assigned: {counts['assigned']}\n\n"
    text += "What do you want to delete?"

    markup = types.InlineKeyboardMarkup()

    if counts['available'] > 0:
        markup.add(types.InlineKeyboardButton(
            f"Delete Available ({counts['available']})",
            callback_data=f"delconfirm_{service_type}_{country}_available"
        ))

    if counts['total'] > 0:
        markup.add(types.InlineKeyboardButton(
            f"⚠️ Delete All ({counts['total']})",
            callback_data=f"delconfirm_{service_type}_{country}_all"
        ))

    markup.add(types.InlineKeyboardButton(
        "❌ Cancel",
        callback_data="delcancel"
    ))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delconfirm_'))
def delete_confirm(call):
    parts = call.data.split('_')
    service_type = parts[1]
    delete_scope = parts[-1]
    country = '_'.join(parts[2:-1])

    delete_all = (delete_scope == 'all')

    deleted_count = delete_numbers(service_type, country, delete_all)

    text = f"✅ Deleted {deleted_count} numbers!\n\n"
    text += f"Service: {service_type}\n"
    text += f"Country: {country}\n"
    text += f"Type: {'All numbers' if delete_all else 'Available only'}"

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )

    bot.answer_callback_query(call.id, f"✅ {deleted_count} numbers deleted!")

@bot.callback_query_handler(func=lambda call: call.data == 'delcancel')
def delete_cancel(call):
    bot.edit_message_text(
        "❌ Delete cancelled.",
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id, "Cancelled")

@bot.callback_query_handler(func=lambda call: call.data == 'no_numbers')
def no_numbers_available(call):
    bot.answer_callback_query(call.id, "No numbers available. Contact admin.")

@bot.callback_query_handler(func=lambda call: call.data == 'tempmail_show_providers')
@require_membership_callback
def tempmail_show_providers(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for provider_key, provider_info in TEMP_MAIL_PROVIDERS.items():
        markup.add(types.InlineKeyboardButton(
            provider_info['name'], 
            callback_data=f"tempmail_select_{provider_key}"
        ))
    
    text = "🌐 Select Temp Mail Provider:\n\n✅ Guerrillamail সবচেয়ে ভালো কাজ করে!\n\n⚠️ নোট: Facebook, Instagram এবং কিছু banking websites temp mail block করে। এটা temp mail service এর সমস্যা নয়, website এর policy।\n\n💡 টিপস:\n• সাধারণ registration এ Guerrillamail ব্যবহার করুন\n• একাধিক provider try করুন\n• কিছু website temp mail accept করে না"
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id, "Select a provider")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tempmail_select_'))
@require_membership_callback
def tempmail_generate_with_provider(call):
    provider_key = call.data.replace('tempmail_select_', '')
    
    bot.answer_callback_query(call.id, "⏳ Generating email...")
    
    try:
        email, token, selected_provider = generate_temp_email(provider_key)
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Failed to generate email. Try again later.", show_alert=True)
        return

    if email and token and selected_provider:
        user_temp_emails[call.message.chat.id] = email
        user_email_tokens[call.message.chat.id] = token
        user_selected_provider[call.message.chat.id] = selected_provider

        provider = TEMP_MAIL_PROVIDERS[selected_provider]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📬 Inbox", callback_data="tempmail_inbox"))
        markup.add(types.InlineKeyboardButton("🔄 Change Mail", callback_data="tempmail_show_providers"))
        markup.add(types.InlineKeyboardButton("🗑 Delete Mail", callback_data="tempmail_delete"))

        text = f"✅ Temp Mail Generated!\n\n📧 Email: {email}\n\n🌐 Provider: {provider['name']}\n\nTap to copy!\n\nThis email is active and ready to receive messages."

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Try Another Provider", callback_data="tempmail_show_providers"))
        
        text = "❌ Failed to generate email with this provider.\n\nPlease try another provider."
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == 'tempmail_inbox')
@require_membership_callback
def tempmail_inbox(call):
    current_email = user_temp_emails.get(call.message.chat.id)
    sid_token = user_email_tokens.get(call.message.chat.id)
    provider_key = user_selected_provider.get(call.message.chat.id, 'guerrilla_com')

    if not current_email or not sid_token:
        bot.answer_callback_query(call.id, "❌ Please generate an email first!")
        return

    bot.answer_callback_query(call.id, "⏳ Loading inbox...")

    try:
        messages = check_temp_email_inbox(sid_token, provider_key)
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Failed to fetch inbox.", show_alert=True)
        return

    real_messages = [msg for msg in messages if msg.get('mail_from', '').lower() not in ['no-reply@guerrillamail.com', 'no-reply@guerrillamail.net']]

    if real_messages:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="tempmail_inbox"))
        markup.add(types.InlineKeyboardButton("🔄 Change Mail", callback_data="tempmail_show_providers"))
        markup.add(types.InlineKeyboardButton("🗑 Delete Mail", callback_data="tempmail_delete"))

        text = f"📬 Inbox for {current_email}\n\n"
        text += f"You have {len(real_messages)} message(s):\n\n"

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

        for idx, msg in enumerate(real_messages[:10], 1):
            msg_id = msg.get('mail_id')
            subject = msg.get('mail_subject', 'No Subject')
            sender = msg.get('mail_from', 'Unknown')
            date = msg.get('mail_date', '')

            msg_text = f"📬 Inbox #{idx}\n"
            msg_text += f"🆔 Id : {msg_id}\n"
            msg_text += f"✉️ To : {current_email}\n"
            msg_text += f"📋 Subject : {subject}\n"
            msg_text += f"📩 From : {sender}\n"
            msg_text += f"💬 Message : "

            try:
                full_msg, error = read_temp_email_message(sid_token, msg_id, provider_key)
                if full_msg:
                    raw_body = full_msg.get('mail_body', 'No content')
                    body_text, links = clean_html_content(raw_body)
                    
                    preview = body_text[:300] if len(body_text) > 300 else body_text
                    msg_text += f"{body_text}\n"
                    
                    if links:
                        msg_text += "\n🔗 Links:\n"
                        for link in links[:5]:
                            msg_text += f"• {link}\n"
                elif error:
                    msg_text += f"[Temporary API issue: {error}]\n"
                else:
                    msg_text += "[Unable to load message content]\n"
            except Exception as e:
                print(f"Error displaying email: {e}")
                msg_text += f"[Error displaying message]\n"

            msg_text += "\n" + "─" * 30 + "\n"

            if len(msg_text) > 4000:
                chunks = [msg_text[i:i+4000] for i in range(0, len(msg_text), 4000)]
                for chunk in chunks:
                    bot.send_message(call.message.chat.id, chunk, disable_web_page_preview=True)
            else:
                bot.send_message(call.message.chat.id, msg_text, disable_web_page_preview=True)

    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="tempmail_inbox"))
        markup.add(types.InlineKeyboardButton("🔄 Change Mail", callback_data="tempmail_show_providers"))
        markup.add(types.InlineKeyboardButton("🗑 Delete Mail", callback_data="tempmail_delete"))

        text = f"📬 Inbox for {current_email}\n\n📭 এখনো কোনো মেইল আসেনি।\n\nCheck back later!"

        try:
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                print(f"Error updating inbox message: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'tempmail_delete')
@require_membership_callback
def tempmail_delete(call):
    if call.message.chat.id in user_temp_emails:
        deleted_email = user_temp_emails[call.message.chat.id]
        del user_temp_emails[call.message.chat.id]
        if call.message.chat.id in user_email_tokens:
            del user_email_tokens[call.message.chat.id]
        if call.message.chat.id in user_selected_provider:
            del user_selected_provider[call.message.chat.id]

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📧 Get Mail", callback_data="tempmail_show_providers"))

        text = f"✅ Email Deleted!\n\n🗑 {deleted_email}\n\nYour temp mail has been deleted successfully."

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "✅ Email deleted!")
    else:
        bot.answer_callback_query(call.id, "❌ No email to delete!")

@bot.message_handler(func=lambda message: message.chat.id in user_fake_address_state and user_fake_address_state[message.chat.id])
@require_membership
def handle_fake_address_input(message):
    user_id = message.chat.id
    user_fake_address_state[user_id] = False
    process_fake_address(message)

@bot.message_handler(func=lambda message: message.chat.id in user_country_lookup_state and user_country_lookup_state[message.chat.id])
@require_membership
def handle_country_lookup_input(message):
    user_id = message.chat.id
    user_country_lookup_state[user_id] = False
    process_country_lookup(message)

print("🤖 Bot is starting...")
print(f"✅ Admin ID: {ADMIN_CHAT_ID}")
print("📡 Polling for messages...")

# যদি আপনার ছবিতে দেখানো 'ModuleNotFoundError' -এর মতো ত্রুটি হয়,
# তাহলে আপনাকে 'pip install PyTelegramBotAPI sqlite3 faker phonenumbers'
# কমান্ডটি রান করে প্রয়োজনীয় লাইব্রেরিগুলো ইনস্টল করতে হবে।
# SyntaxError -এর কারণ হতে পারে ভুল কমান্ড লাইনে টাইপিং, যা ছবিতে দেখা যাচ্ছে।
# আপডেটেড কোডটি সঠিক সিনট্যাক্স অনুসরণ করেছে।

bot.infinity_polling()
