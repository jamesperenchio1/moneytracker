"""Auto-categorize transactions based on description keywords and pattern detection."""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.transaction import CategoryName, Category, Transaction


# Keyword → category mapping for Thai banking transactions
CATEGORY_KEYWORDS: dict[CategoryName, list[str]] = {
    CategoryName.FOOD: [
        "grab food", "foodpanda", "lineman", "restaurant", "cafe", "coffee",
        "starbucks", "mcdonald", "kfc", "pizza", "7-eleven", "7eleven",
        "family mart", "tops", "big c", "makro", "lotus", "villa market",
        "gourmet", "sizzler", "bar-b-q", "shabushi", "mk restaurant",
        "sukishi", "yakiniku", "sushi", "eatery", "bakery", "อาหาร",
        "ร้านอาหาร", "กาแฟ", "swensen", "burger king", "dairy queen",
        "ข้าว", "เครื่องดื่ม", "ชานม", "ชาไข่มุก", "บะหมี่", "ก๋วยเตี๋ยว",
        "ส้มตำ", "อาหารทะเล", "ไก่ทอด", "domino", "papa john",
        "bonchon", "bar b q", "hot pot", "dim sum", "ติ่มซำ",
        "after you", "mango tango", "krispy kreme", "dunkin",
        "เบเกอรี่", "ขนม", "snack", "เค้ก", "ice cream", "ไอศกรีม",
        "food", "dine", "dining", "lunch", "dinner", "breakfast",
        "โออิชิ", "oishi", "fuji", "yayoi", "coco", "chatime",
    ],
    CategoryName.TRANSPORTATION: [
        "grab", "bolt", "bts", "mrt", "airport link", "taxi", "fuel",
        "shell", "ptt", "esso", "caltex", "bangchak", "toll", "parking",
        "expressway", "รถไฟ", "แท็กซี่", "น้ำมัน", "grab car", "indriver",
        "วินมอเตอร์ไซค์", "ค่าทางด่วน", "uber", "robinhood", "แกร็บ",
        "ค่ารถ", "ค่าเดินทาง", "transit", "bus", "รถเมล์",
        "ค่าจอดรถ", "car wash", "ล้างรถ", "ค่าผ่านทาง",
    ],
    CategoryName.RENT: [
        "rent", "ค่าเช่า", "condo", "apartment", "housing", "lease",
        "ค่าห้อง", "หอพัก", "ค่าบ้าน", "property",
    ],
    CategoryName.UTILITIES: [
        "electric", "water", "internet", "true", "ais", "dtac", "3bb",
        "tot", "pea", "mwa", "mea", "ไฟฟ้า", "น้ำประปา", "อินเทอร์เน็ต",
        "ค่าโทรศัพท์", "ค่าไฟ", "ค่าน้ำ", "ค่าเน็ต", "phone bill",
        "mobile", "broadband", "fiber", "ค่าโทร",
    ],
    CategoryName.SUBSCRIPTIONS: [
        "netflix", "spotify", "youtube", "apple", "google", "icloud",
        "hbo", "disney", "amazon prime", "subscription", "monthly",
        "premium", "membership", "สมาชิก",
    ],
    CategoryName.INCOME: [
        "salary", "payroll", "bonus", "dividend", "interest", "refund",
        "เงินเดือน", "โบนัส", "chromalloy", "net pay", "payslip",
        "income", "commission earned", "reimbursement", "คืนเงิน",
        "เงินปันผล", "ดอกเบี้ย",
    ],
    CategoryName.TRANSFERS: [
        "transfer", "โอน", "promptpay", "พร้อมเพย์", "โอนเงิน",
        "kbank", "scb", "bbl", "ktb", "tmb", "ttb", "krungsri",
        "ธนาคาร", "โอนระหว่าง", "wire", "remittance",
    ],
    CategoryName.SHOPPING: [
        "shopee", "lazada", "central", "robinson", "mall", "uniqlo",
        "h&m", "zara", "nike", "adidas", "siam", "terminal 21",
        "jd central", "powerbuy", "pantip", "it city", "banana",
        "tesco", "amazon", "aliexpress", "taobao", "online shop",
        "ซื้อของ", "ช้อปปิ้ง", "ห้าง",
    ],
    CategoryName.ENTERTAINMENT: [
        "cinema", "movie", "sf cinema", "major", "concert", "game",
        "steam", "playstation", "nintendo", "karaoke", "bowling",
        "ภาพยนตร์", "เกม", "ท่องเที่ยว", "travel", "hotel", "booking",
        "agoda", "airbnb", "hostel", "resort",
    ],
    CategoryName.HEALTHCARE: [
        "hospital", "pharmacy", "clinic", "doctor", "dental", "boots",
        "watsons", "โรงพยาบาล", "ร้านยา", "ยา", "สุขภาพ", "ทันตกรรม",
        "แพทย์", "health", "medical", "ประกัน",
    ],
    CategoryName.EDUCATION: [
        "school", "university", "course", "udemy", "coursera", "tuition",
        "มหาวิทยาลัย", "โรงเรียน", "เรียน", "training", "workshop",
        "skillshare", "linkedin learning",
    ],
    CategoryName.INVESTMENT: [
        "invest", "stock", "fund", "mutual fund", "กองทุน",
        "หุ้น", "ลงทุน", "etf", "bond", "พันธบัตร",
    ],
}


def infer_category(description: str) -> CategoryName | None:
    """Infer transaction category from description text using keyword matching."""
    if not description:
        return None

    desc_lower = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category

    return None


def suggest_categories(
    description: str,
    db: Optional[Session] = None,
) -> list[tuple[CategoryName, float]]:
    """Return top-3 category suggestions ranked by confidence.

    1. Keyword match → confidence 1.0
    2. Pattern match from previously-categorized transactions → confidence 0.5–0.9
    """
    if not description:
        return []

    suggestions: list[tuple[CategoryName, float]] = []
    desc_lower = description.lower()

    # 1. Keyword matches
    keyword_matches: dict[CategoryName, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                keyword_matches[category] = keyword_matches.get(category, 0) + 1

    for cat, count in sorted(keyword_matches.items(), key=lambda x: -x[1]):
        suggestions.append((cat, min(1.0, 0.7 + count * 0.1)))

    # 2. Pattern matching from DB (previously categorized transactions)
    if db and len(suggestions) < 3:
        seen_cats = {s[0] for s in suggestions}
        pattern_results = _match_patterns_from_db(desc_lower, db, exclude=seen_cats)
        suggestions.extend(pattern_results)

    return suggestions[:3]


def _match_patterns_from_db(
    desc_lower: str,
    db: Session,
    exclude: set[CategoryName] | None = None,
) -> list[tuple[CategoryName, float]]:
    """Find categories of previously-categorized transactions with similar descriptions."""
    exclude = exclude or set()
    results = []

    # Extract significant words (3+ chars, skip common words)
    stop_words = {
        "the", "and", "for", "from", "with", "this", "that", "will",
        "has", "have", "had", "been", "was", "are", "not", "but",
        "จาก", "ถึง", "ของ", "ใน", "ที่", "ให้", "ได้", "ไป", "มา",
    }
    words = [w for w in desc_lower.split() if len(w) >= 3 and w not in stop_words]

    if not words:
        return results

    # Query for each significant word
    category_scores: dict[CategoryName, float] = {}

    for word in words[:5]:  # Limit to 5 words
        try:
            rows = db.execute(
                select(
                    Category.name,
                    func.count(Transaction.id).label("cnt"),
                )
                .join(Transaction.category)
                .where(
                    Transaction.description.ilike(f"%{word}%"),
                    Transaction.category_id.isnot(None),
                )
                .group_by(Category.name)
                .order_by(func.count(Transaction.id).desc())
                .limit(3)
            ).all()

            for row in rows:
                cat_name = row[0]
                count = row[1]
                if cat_name not in exclude:
                    # Scale confidence by match count
                    confidence = min(0.9, 0.5 + (count / 20) * 0.4)
                    current = category_scores.get(cat_name, 0)
                    category_scores[cat_name] = max(current, confidence)
        except Exception:
            continue

    for cat, score in sorted(category_scores.items(), key=lambda x: -x[1]):
        results.append((cat, score))

    return results[:3]


def infer_category_with_patterns(
    description: str,
    db: Optional[Session] = None,
) -> CategoryName | None:
    """Infer category using keywords first, then DB pattern matching as fallback."""
    # Try keyword matching first
    result = infer_category(description)
    if result:
        return result

    # Fallback to pattern matching from DB
    if db:
        suggestions = _match_patterns_from_db(description.lower() if description else "", db)
        if suggestions and suggestions[0][1] >= 0.6:
            return suggestions[0][0]

    return None
