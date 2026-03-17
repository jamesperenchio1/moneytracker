"""Auto-categorize transactions based on description keywords."""

from app.models.transaction import CategoryName

# Keyword → category mapping for Thai banking transactions
CATEGORY_KEYWORDS: dict[CategoryName, list[str]] = {
    CategoryName.FOOD: [
        "grab food", "foodpanda", "lineman", "restaurant", "cafe", "coffee",
        "starbucks", "mcdonald", "kfc", "pizza", "7-eleven", "7eleven",
        "family mart", "tops", "big c", "makro", "lotus", "villa market",
        "gourmet", "sizzler", "bar-b-q", "shabushi", "mk restaurant",
        "sukishi", "yakiniku", "sushi", "eatery", "bakery", "อาหาร",
        "ร้านอาหาร", "กาแฟ",
    ],
    CategoryName.TRANSPORTATION: [
        "grab", "bolt", "bts", "mrt", "airport link", "taxi", "fuel",
        "shell", "ptt", "esso", "caltex", "bangchak", "toll", "parking",
        "expressway", "รถไฟ", "แท็กซี่", "น้ำมัน",
    ],
    CategoryName.RENT: [
        "rent", "ค่าเช่า", "condo", "apartment", "housing", "lease",
    ],
    CategoryName.UTILITIES: [
        "electric", "water", "internet", "true", "ais", "dtac", "3bb",
        "tot", "pea", "mwa", "mea", "ไฟฟ้า", "น้ำประปา", "อินเทอร์เน็ต",
    ],
    CategoryName.SUBSCRIPTIONS: [
        "netflix", "spotify", "youtube", "apple", "google", "icloud",
        "hbo", "disney", "amazon prime", "subscription", "monthly",
    ],
    CategoryName.INCOME: [
        "salary", "payroll", "bonus", "dividend", "interest", "refund",
        "เงินเดือน", "โบนัส",
    ],
    CategoryName.TRANSFERS: [
        "transfer", "โอน", "promptpay", "พร้อมเพย์",
    ],
    CategoryName.SHOPPING: [
        "shopee", "lazada", "central", "robinson", "mall", "uniqlo",
        "h&m", "zara", "nike", "adidas", "siam", "terminal 21",
    ],
    CategoryName.ENTERTAINMENT: [
        "cinema", "movie", "sf cinema", "major", "concert", "game",
        "steam", "playstation", "nintendo",
    ],
    CategoryName.HEALTHCARE: [
        "hospital", "pharmacy", "clinic", "doctor", "dental", "boots",
        "watsons", "โรงพยาบาล",
    ],
    CategoryName.EDUCATION: [
        "school", "university", "course", "udemy", "coursera", "tuition",
    ],
    CategoryName.INVESTMENT: [
        "invest", "stock", "fund", "mutual fund", "กองทุน",
    ],
    CategoryName.CREDIT_CARD_PAYMENT: [
        "credit card", "credit card payment", "cc payment", "creditcard",
        "visa payment", "mastercard payment", "amex payment",
        "บัตรเครดิต", "ชำระบัตร", "ชำระค่าบัตร",
    ],
}


def infer_category(description: str) -> CategoryName | None:
    """Infer transaction category from description text."""
    if not description:
        return None

    desc_lower = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category

    return None
