from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import json
import os
from datetime import datetime
import asyncio
from pathlib import Path

# Initialize FastMCP server
mcp = FastMCP("food-tracker")

# Constants
OFF_API_BASE = "https://world.openfoodfacts.net/api/v2"
USER_AGENT = "food-tracker-mcp/1.0"
DATA_DIR = Path("./data")

# ====== Models ======

class Nutrient(BaseModel):
    name: str
    amount: float
    unit: str
    
class NutritionData(BaseModel):
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    sugar: float = 0
    sodium: float = 0
    other_nutrients: List[Nutrient] = []

class ProductInfo(BaseModel):
    id: str
    name: str
    brands: Optional[str] = None
    quantity: Optional[str] = None
    ingredients_text: Optional[str] = None
    nutrition: NutritionData
    image_url: Optional[str] = None
    nova_group: Optional[int] = None
    nutriscore: Optional[str] = None
    
class UserRestriction(BaseModel):
    type: str  # "allergen", "diet", "ingredient", "medical", "preference"
    value: str
    severity: str = "avoid" # "avoid", "limit", "fatal"
    notes: Optional[str] = None

class User(BaseModel):
    id: str
    restrictions: List[UserRestriction] = []
    nutrition_goals: Dict[str, float] = {}

# ====== Data Persistence ======

def ensure_data_directory():
    """Ensure the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DATA_DIR / "users", exist_ok=True)
    os.makedirs(DATA_DIR / "logs", exist_ok=True)

def save_user(user: User) -> bool:
    """Save a user to a JSON file."""
    ensure_data_directory()
    try:
        user_path = DATA_DIR / "users" / f"{user.id}.json"
        with open(user_path, "w") as f:
            json.dump(user.dict(), f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving user: {e}")
        return False

def load_user(user_id: str) -> Optional[User]:
    """Load a user from a JSON file."""
    ensure_data_directory()
    user_path = DATA_DIR / "users" / f"{user_id}.json"
    if not user_path.exists():
        return None
    
    try:
        with open(user_path, "r") as f:
            user_data = json.load(f)
        return User(**user_data)
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

def load_all_users() -> Dict[str, User]:
    """Load all users from JSON files."""
    ensure_data_directory()
    users_dict = {}
    user_files = (DATA_DIR / "users").glob("*.json")
    
    for user_file in user_files:
        try:
            with open(user_file, "r") as f:
                user_data = json.load(f)
            user_id = user_data.get("id")
            if user_id:
                users_dict[user_id] = User(**user_data)
        except Exception as e:
            print(f"Error loading user file {user_file}: {e}")
    
    return users_dict

def log_food_entry(user_id: str, product_data: Dict[str, Any], quantity: float, meal_type: str) -> bool:
    """Log a food entry to the user's food log file."""
    ensure_data_directory()
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = DATA_DIR / "logs" / f"{user_id}_{today}.json"
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "product": product_data,
        "quantity": quantity,
        "meal_type": meal_type
    }
    
    entries = []
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                entries = json.load(f)
        except json.JSONDecodeError:
            # If file is corrupted, start with empty list
            entries = []
    
    entries.append(entry)
    
    try:
        with open(log_file, "w") as f:
            json.dump(entries, f, indent=2)
        return True
    except Exception as e:
        print(f"Error logging food entry: {e}")
        return False

def get_food_log(user_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get a user's food log for a specific date."""
    ensure_data_directory()
    
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    log_file = DATA_DIR / "logs" / f"{user_id}_{date}.json"
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading food log: {e}")
        return []

# ====== Helper Functions ======

async def make_off_request(path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to the Open Food Facts API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    url = f"{OFF_API_BASE}{path}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

def extract_nutrition_data(product_data: Dict[str, Any]) -> NutritionData:
    """Extract structured nutrition data from product data."""
    nutriments = product_data.get("nutriments", {})
    
    return NutritionData(
        calories=nutriments.get("energy-kcal_100g", 0),
        protein=nutriments.get("proteins_100g", 0),
        carbs=nutriments.get("carbohydrates_100g", 0),
        fat=nutriments.get("fat_100g", 0),
        fiber=nutriments.get("fiber_100g", 0),
        sugar=nutriments.get("sugars_100g", 0),
        sodium=nutriments.get("sodium_100g", 0)
    )

def format_product_info(product_data: Dict[str, Any]) -> ProductInfo:
    """Format product data into a structured ProductInfo object."""
    nutrition = extract_nutrition_data(product_data)
    
    return ProductInfo(
        id=product_data.get("code", ""),
        name=product_data.get("product_name", "Unknown Product"),
        brands=product_data.get("brands", None),
        quantity=product_data.get("quantity", None),
        ingredients_text=product_data.get("ingredients_text", None),
        nutrition=nutrition,
        image_url=product_data.get("image_url", None),
        nova_group=product_data.get("nova_group", None),
        nutriscore=product_data.get("nutriscore_grade", None)
    )

def check_compatibility(product: ProductInfo, restrictions: List[UserRestriction]) -> Dict[str, Any]:
    """Check if a product is compatible with user restrictions."""
    incompatibilities = []
    warnings = []
    
    for restriction in restrictions:
        # Check allergens
        if restriction.type == "allergen":
            allergen = restriction.value.lower()
            
            # Check ingredients text
            if product.ingredients_text and allergen in product.ingredients_text.lower():
                severity = "High" if restriction.severity == "fatal" else "Medium"
                incompatibilities.append({
                    "restriction": restriction.value,
                    "severity": severity,
                    "reason": f"Contains {restriction.value}"
                })
        
        # Check diet restrictions (simplified)
        if restriction.type == "diet" and restriction.value == "vegetarian":
            meat_ingredients = ["beef", "chicken", "pork", "meat", "fish"]
            if product.ingredients_text:
                for ingredient in meat_ingredients:
                    if ingredient in product.ingredients_text.lower():
                        incompatibilities.append({
                            "restriction": "vegetarian",
                            "severity": "Medium",
                            "reason": f"Contains non-vegetarian ingredient: {ingredient}"
                        })
    
    return {
        "compatible": len(incompatibilities) == 0,
        "incompatibilities": incompatibilities,
        "warnings": warnings
    }

# ====== User Management with Persistence ======

# Load users at startup
users = {}  # In-memory cache

def get_user(user_id: str) -> Optional[User]:
    """Get a user by ID, or return None if not found."""
    # Check in-memory cache first
    if user_id in users:
        return users[user_id]
    
    # Try to load from file
    user = load_user(user_id)
    if user:
        # Update cache
        users[user_id] = user
    
    return user

def create_or_update_user(user: User) -> User:
    """Create or update a user in both cache and storage."""
    users[user.id] = user  # Update cache
    save_user(user)  # Persist to disk
    return user

# ====== MCP Tools ======

@mcp.tool()
async def get_product_by_barcode(barcode: str) -> Dict[str, Any]:
    """
    Get detailed information about a food product by barcode.
    
    Args:
        barcode: The product barcode (EAN, UPC, etc.)
    """
    response = await make_off_request(f"/product/{barcode}")
    
    if "error" in response:
        return {"found": False, "error": response["error"]}
    
    if response.get("status") != 1:
        return {"found": False, "error": "Product not found"}
    
    product_data = response.get("product", {})
    product_info = format_product_info(product_data)
    
    return {
        "found": True,
        "product": product_info.dict()
    }

@mcp.tool()
async def search_products(query: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """
    Search for food products by name or description.
    
    Args:
        query: The search query
        page: Page number for pagination (default: 1)
        page_size: Number of results per page (default: 10)
    """
    params = {
        "search_terms": query,
        "page": page,
        "page_size": page_size
    }
    
    response = await make_off_request("/search", params)
    
    if "error" in response:
        return {"success": False, "error": response["error"]}
    
    products = []
    for p in response.get("products", []):
        product_info = format_product_info(p)
        products.append(product_info.dict())
    
    return {
        "success": True,
        "count": response.get("count", 0),
        "page": response.get("page", 1),
        "products": products
    }

@mcp.tool()
async def manage_user_restrictions(
    user_id: str,
    action: str,  # "get", "add", "remove", "update"
    restriction_type: Optional[str] = None,  # "allergen", "diet", "ingredient", "medical", "preference"
    restriction_value: Optional[str] = None,
    severity: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manage a user's dietary restrictions.
    
    Args:
        user_id: The user's unique identifier
        action: The action to perform (get, add, remove, update)
        restriction_type: Type of restriction (allergen, diet, ingredient, medical, preference)
        restriction_value: The specific restriction value (e.g., "peanuts", "vegetarian")
        severity: How severe the restriction is (avoid, limit, fatal)
        notes: Additional notes about the restriction
    """
    # Get or create user
    user = get_user(user_id)
    if not user:
        user = User(id=user_id)
        create_or_update_user(user)
    
    if action == "get":
        return {"restrictions": [r.dict() for r in user.restrictions]}
    
    elif action == "add":
        if not restriction_type or not restriction_value:
            return {"success": False, "error": "restriction_type and restriction_value required for add action"}
        
        new_restriction = UserRestriction(
            type=restriction_type,
            value=restriction_value,
            severity=severity or "avoid",
            notes=notes
        )
        
        # Check if already exists
        for i, r in enumerate(user.restrictions):
            if r.type == restriction_type and r.value == restriction_value:
                user.restrictions[i] = new_restriction
                create_or_update_user(user)
                return {"success": True, "message": "Restriction updated", "restrictions": [r.dict() for r in user.restrictions]}
        
        # Add new restriction
        user.restrictions.append(new_restriction)
        create_or_update_user(user)
        return {"success": True, "message": "Restriction added", "restrictions": [r.dict() for r in user.restrictions]}
    
    elif action == "remove":
        if not restriction_type or not restriction_value:
            return {"success": False, "error": "restriction_type and restriction_value required for remove action"}
        
        # Find and remove restriction
        new_restrictions = []
        found = False
        for r in user.restrictions:
            if r.type == restriction_type and r.value == restriction_value:
                found = True
            else:
                new_restrictions.append(r)
        
        if not found:
            return {"success": False, "error": "Restriction not found"}
        
        user.restrictions = new_restrictions
        create_or_update_user(user)
        return {"success": True, "message": "Restriction removed", "restrictions": [r.dict() for r in user.restrictions]}
    
    return {"success": False, "error": f"Unknown action: {action}"}

@mcp.tool()
async def check_product_compatibility(
    user_id: str,
    barcode: str
) -> Dict[str, Any]:
    """
    Check if a product is compatible with a user's dietary restrictions.
    
    Args:
        user_id: The user's unique identifier
        barcode: The product barcode to check
    """
    # Get user
    user = get_user(user_id)
    if not user:
        return {"success": False, "error": "User not found"}
    
    # Get product
    product_response = await get_product_by_barcode(barcode)
    if not product_response.get("found", False):
        return {"success": False, "error": "Product not found"}
    
    product_info = ProductInfo(**product_response["product"])
    
    # Check compatibility
    compatibility = check_compatibility(product_info, user.restrictions)
    
    return {
        "success": True,
        "product_name": product_info.name,
        "compatibility": compatibility
    }

@mcp.tool()
async def analyze_nutrition(barcode: str) -> Dict[str, Any]:
    """
    Analyze the nutritional content of a food product.
    
    Args:
        barcode: The product barcode
    """
    # Get product
    product_response = await get_product_by_barcode(barcode)
    if not product_response.get("found", False):
        return {"success": False, "error": "Product not found"}
    
    product_info = ProductInfo(**product_response["product"])
    nutrition = product_info.nutrition
    
    # Calculate basic macronutrient percentages
    total_calories = 0
    calories_from_protein = nutrition.protein * 4
    calories_from_carbs = nutrition.carbs * 4
    calories_from_fat = nutrition.fat * 9
    
    total_calories = calories_from_protein + calories_from_carbs + calories_from_fat
    
    # Avoid division by zero
    if total_calories > 0:
        protein_percent = (calories_from_protein / total_calories) * 100
        carbs_percent = (calories_from_carbs / total_calories) * 100
        fat_percent = (calories_from_fat / total_calories) * 100
    else:
        protein_percent = carbs_percent = fat_percent = 0
    
    # Nutritional assessment (simplified)
    assessment = []
    
    # Protein assessment
    if protein_percent < 10:
        assessment.append("Low in protein")
    elif protein_percent > 30:
        assessment.append("High in protein")
    
    # Sugar assessment
    if nutrition.sugar > 10:
        assessment.append("High in sugar")
    
    # Fiber assessment
    if nutrition.fiber < 3:
        assessment.append("Low in fiber")
    elif nutrition.fiber > 6:
        assessment.append("High in fiber")
    
    return {
        "success": True,
        "product_name": product_info.name,
        "nutrition": nutrition.dict(),
        "macronutrient_breakdown": {
            "protein_percent": round(protein_percent, 1),
            "carbs_percent": round(carbs_percent, 1),
            "fat_percent": round(fat_percent, 1)
        },
        "assessment": assessment,
        "nova_group": product_info.nova_group,
        "nutriscore": product_info.nutriscore
    }

@mcp.tool()
async def log_food_consumption(
    user_id: str,
    barcode: str,
    quantity: float = 1.0,
    meal_type: str = "snack"  # breakfast, lunch, dinner, snack
) -> Dict[str, Any]:
    """
    Log food consumption for a user.
    
    Args:
        user_id: The user's unique identifier
        barcode: The product barcode
        quantity: Amount consumed (default: 1 serving)
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
    """
    # Get product
    product_response = await get_product_by_barcode(barcode)
    if not product_response.get("found", False):
        return {"success": False, "error": "Product not found"}
    
    product_info = ProductInfo(**product_response["product"])
    
    # Get user
    user = get_user(user_id)
    if not user:
        user = User(id=user_id)
        create_or_update_user(user)
    
    # Check compatibility
    compatibility = check_compatibility(product_info, user.restrictions)
    
    # Calculate nutrition based on quantity
    nutrition = product_info.nutrition
    
    # Prepare simplified product data for logging
    product_data = {
        "name": product_info.name,
        "barcode": barcode,
        "brands": product_info.brands,
        "nutrition": {
            "calories": nutrition.calories * quantity,
            "protein": nutrition.protein * quantity,
            "carbs": nutrition.carbs * quantity,
            "fat": nutrition.fat * quantity
        }
    }
    
    # Log the food consumption
    log_success = log_food_entry(user_id, product_data, quantity, meal_type)
    
    return {
        "success": True,
        "message": f"Logged {quantity} serving(s) of {product_info.name} as {meal_type}",
        "persisted": log_success,
        "product": {
            "name": product_info.name,
            "barcode": barcode
        },
        "compatibility": compatibility,
        "nutrition_consumed": {
            "calories": nutrition.calories * quantity,
            "protein": nutrition.protein * quantity,
            "carbs": nutrition.carbs * quantity,
            "fat": nutrition.fat * quantity
        }
    }

@mcp.tool()
async def get_user_food_log(
    user_id: str,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a user's food log for a specific date.
    
    Args:
        user_id: The user's unique identifier
        date: Date in YYYY-MM-DD format (defaults to today)
    """
    # Get user
    user = get_user(user_id)
    if not user:
        return {"success": False, "error": "User not found"}
    
    # Get food log
    log_entries = get_food_log(user_id, date)
    
    # Calculate nutrition totals
    total_nutrition = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0
    }
    
    for entry in log_entries:
        if "nutrition" in entry.get("product", {}):
            nutrition = entry["product"]["nutrition"]
            total_nutrition["calories"] += nutrition.get("calories", 0)
            total_nutrition["protein"] += nutrition.get("protein", 0)
            total_nutrition["carbs"] += nutrition.get("carbs", 0)
            total_nutrition["fat"] += nutrition.get("fat", 0)
    
    return {
        "success": True,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "entries": log_entries,
        "nutrition_totals": total_nutrition
    }

# Initialize data directory at startup
ensure_data_directory()

# Initialize and run the server
if __name__ == "__main__":
    # Make sure data directories exist
    ensure_data_directory()
    # Load any existing users
    users = load_all_users()
    print(f"Loaded {len(users)} users from storage")
    # Run the server
    mcp.run(transport='stdio')