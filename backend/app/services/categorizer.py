"""Auto-categorize transactions based on description keywords."""

from app.models.transaction import CategoryName

# ---------------------------------------------------------------------------
# Categories that represent money flow but are NOT real income or spending.
# These should be excluded from income/expense totals in analytics.
# ---------------------------------------------------------------------------
TRANSFER_CATEGORIES = {
    CategoryName.TRANSFERS,
    CategoryName.TRANSFER_IN,
    CategoryName.TRANSFER_OUT,
}

# Keyword → category mapping for Thai banking transactions.
# Order matters: more specific matches should come before broad ones.
CATEGORY_KEYWORDS: dict[CategoryName, list[str]] = {
    # ------------------------------------------------------------------ #
    # Real income — salary, dividends, interest, etc.
    # ------------------------------------------------------------------ #
    CategoryName.INCOME: [
        "salary", "payroll", "payslip", "wages", "bonus", "commission",
        "dividend", "dividends", "interest income", "interest earned",
        "coupon", "refund", "reimbursement", "cashback", "rebate",
        "เงินเดือน", "โบนัส", "ดอกเบี้ย", "เงินคืน",
    ],

    # ------------------------------------------------------------------ #
    # Transfers — money moving between people or accounts (not income/expense)
    # Direction is resolved in tasks.py based on CREDIT vs DEBIT type.
    # ------------------------------------------------------------------ #
    CategoryName.TRANSFERS: [
        # Thai PromptPay / mobile banking keywords
        "promptpay", "พร้อมเพย์", "pp ref", "ppref",
        "โอน", "โอนเงิน", "รับโอน", "โอนจาก", "โอนให้",
        # Generic transfer verbs
        "transfer", "transferred", "wire transfer", "bank transfer",
        "interbank", "bahtnet", "ธนาคาร",
        # Peer names / patterns (generic)
        "from ", "to acct", "from acct",
        "payment from", "received from",
        "sent to", "paid to",
        # ATM / branch
        "atm withdrawal", "cash withdrawal", "withdraw",
        "deposit", "cash deposit",
    ],

    # ------------------------------------------------------------------ #
    # Food & dining
    # ------------------------------------------------------------------ #
    CategoryName.FOOD: [
        "grab food", "foodpanda", "lineman", "restaurant", "cafe", "coffee",
        "starbucks", "mcdonald", "kfc", "pizza", "7-eleven", "7eleven",
        "family mart", "tops", "big c", "makro", "lotus", "villa market",
        "gourmet", "sizzler", "bar-b-q", "shabushi", "mk restaurant",
        "sukishi", "yakiniku", "sushi", "eatery", "bakery", "buffet",
        "อาหาร", "ร้านอาหาร", "กาแฟ", "ข้าว", "ส้มตำ",
    ],

    # ------------------------------------------------------------------ #
    # Transportation
    # ------------------------------------------------------------------ #
    CategoryName.TRANSPORTATION: [
        "grab", "bolt", "bts", "mrt", "airport link", "taxi", "fuel",
        "shell", "ptt", "esso", "caltex", "bangchak", "toll", "parking",
        "expressway", "บขส", "รถไฟ", "แท็กซี่", "น้ำมัน",
        "gasoline", "petrol", "uber", "lyft",
    ],

    # ------------------------------------------------------------------ #
    # Rent & housing
    # ------------------------------------------------------------------ #
    CategoryName.RENT: [
        "rent", "ค่าเช่า", "condo", "condominium", "apartment", "housing",
        "lease", "landlord", "property management",
    ],

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    CategoryName.UTILITIES: [
        "electric", "electricity", "water bill", "internet", "broadband",
        "true", "ais", "dtac", "3bb", "tot", "pea", "mwa", "mea",
        "ไฟฟ้า", "น้ำประปา", "อินเทอร์เน็ต", "ค่าน้ำ", "ค่าไฟ",
        "phone bill", "mobile bill",
    ],

    # ------------------------------------------------------------------ #
    # Subscriptions
    # ------------------------------------------------------------------ #
    CategoryName.SUBSCRIPTIONS: [
        "netflix", "spotify", "youtube premium", "apple music",
        "apple one", "icloud", "google one", "google storage",
        "hbo", "disney+", "amazon prime", "prime video",
        "subscription", "monthly plan",
    ],

    # ------------------------------------------------------------------ #
    # Shopping
    # ------------------------------------------------------------------ #
    CategoryName.SHOPPING: [
        "shopee", "lazada", "central", "robinson", "mall", "uniqlo",
        "h&m", "zara", "nike", "adidas", "siam paragon", "terminal 21",
        "emquartier", "the mall", "ikea", "amazon.com",
    ],

    # ------------------------------------------------------------------ #
    # Entertainment
    # ------------------------------------------------------------------ #
    CategoryName.ENTERTAINMENT: [
        "cinema", "movie", "sf cinema", "major cineplex", "concert",
        "game", "steam", "playstation", "nintendo", "xbox", "twitch",
    ],

    # ------------------------------------------------------------------ #
    # Healthcare
    # ------------------------------------------------------------------ #
    CategoryName.HEALTHCARE: [
        "hospital", "pharmacy", "clinic", "doctor", "dental", "dentist",
        "boots", "watsons", "โรงพยาบาล", "ร้านขายยา", "ยา",
    ],

    # ------------------------------------------------------------------ #
    # Education
    # ------------------------------------------------------------------ #
    CategoryName.EDUCATION: [
        "school", "university", "course", "udemy", "coursera", "tuition",
        "exam fee", "registration fee",
    ],

    # ------------------------------------------------------------------ #
    # Investment
    # ------------------------------------------------------------------ #
    CategoryName.INVESTMENT: [
        "invest", "stock", "etf", "fund", "mutual fund", "กองทุน",
        "brokerage", "securities",
    ],

    # ------------------------------------------------------------------ #
    # Credit card payment (from bank side)
    # ------------------------------------------------------------------ #
    CategoryName.CREDIT_CARD_PAYMENT: [
        "credit card", "credit card payment", "cc payment", "creditcard",
        "visa payment", "mastercard payment", "amex payment",
        "บัตรเครดิต", "ชำระบัตร", "ชำระค่าบัตร",
    ],
}


def infer_category(description: str) -> CategoryName | None:
    """Infer transaction category from description text.

    Returns TRANSFERS for any transfer-like description; the caller in
    tasks.py is responsible for resolving to TRANSFER_IN or TRANSFER_OUT
    based on the actual transaction direction (credit vs debit).
    """
    if not description:
        return None

    desc_lower = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category

    return None


def resolve_transfer_direction(transaction_type: str) -> CategoryName:
    """When a transaction is categorised as TRANSFERS, pin the direction.

    'credit'  → TRANSFER_IN  (money arrived in your account from someone)
    'debit'   → TRANSFER_OUT (money left your account to someone)
    anything else (e.g. 'transfer') → keep generic TRANSFERS
    """
    if transaction_type == "credit":
        return CategoryName.TRANSFER_IN
    if transaction_type == "debit":
        return CategoryName.TRANSFER_OUT
    return CategoryName.TRANSFERS
