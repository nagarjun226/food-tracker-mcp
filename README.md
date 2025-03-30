# Food Tracker MCP

A Model Context Protocol (MCP) server for tracking food consumption, analyzing nutrition, and managing dietary restrictions.

## Overview

Food Tracker MCP integrates with the OpenFoodFacts database to provide a comprehensive food tracking system with the following features:

- Search for food products by barcode or keyword
- Analyze nutritional content of food products
- Create meal plans based on specific nutrition goals and dietary restrictions
- Track food consumption with meal logging
- Manage dietary restrictions and allergies
- Check product compatibility with user restrictions
- View food logs and nutrition summaries

## Installation

### Prerequisites

- Python 3.8 or higher
- `pip` (Python package manager)

### Setup

1. Clone the repository or download the `food_tracker.py` file:

```bash
# Option 1: Clone the repository (if available)
git clone https://github.com/yourusername/food-tracker-mcp.git
cd food-tracker-mcp

# Option 2: Create a new directory and save the file there
mkdir food-tracker-mcp
cd food-tracker-mcp
# Copy food_tracker.py into this directory
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
```

3. Activate the virtual environment:

```bash
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

4. Install the required dependencies:

```bash
pip install httpx fastmcp pydantic
```

5. Ensure the data directories are created (the script will do this automatically on first run):

```bash
mkdir -p data/users data/logs
```

## Running the MCP Server

Run the server using:

```bash
python food_tracker.py
```

The server will start and be ready to receive commands.

## Using with Claude

To use this MCP with Claude, you'll need to register it with the Claude platform. Here's how to do it:

1. Follow Anthropic's documentation to register your MCP:
   - Visit https://console.anthropic.com/mcps or the relevant section in your Anthropic account
   - Register the food-tracker MCP by providing the necessary information and endpoint

2. Once registered, you can interact with the Food Tracker through Claude by invoking the MCP's tools.

Example prompts to use with Claude:

- "Scan this barcode to see nutrition information: 3270190119357"
- "Add a peanut allergy to my dietary restrictions"
- "Log that I had a granola bar for breakfast"
- "Search for products containing 'oatmeal'"
- "Check if this product is compatible with my dietary restrictions"
- "Show me my food log for today"

## Available Tools

This MCP provides the following tools that Claude can access:

### 1. `get_product_by_barcode`

Get detailed information about a food product using its barcode.

**Parameters:**
- `barcode`: The product barcode (EAN, UPC, etc.)

### 2. `search_products`

Search for food products by name or description.

**Parameters:**
- `query`: The search query
- `page`: Page number for pagination (default: 1)
- `page_size`: Number of results per page (default: 10)

### 3. `manage_user_restrictions`

Manage a user's dietary restrictions.

**Parameters:**
- `user_id`: The user's unique identifier
- `action`: The action to perform (get, add, remove, update)
- `restriction_type`: Type of restriction (allergen, diet, ingredient, medical, preference)
- `restriction_value`: The specific restriction value (e.g., "peanuts", "vegetarian")
- `severity`: How severe the restriction is (avoid, limit, fatal)
- `notes`: Additional notes about the restriction

### 4. `check_product_compatibility`

Check if a product is compatible with a user's dietary restrictions.

**Parameters:**
- `user_id`: The user's unique identifier
- `barcode`: The product barcode to check

### 5. `analyze_nutrition`

Analyze the nutritional content of a food product.

**Parameters:**
- `barcode`: The product barcode

### 6. `log_food_consumption`

Log food consumption for a user.

**Parameters:**
- `user_id`: The user's unique identifier
- `barcode`: The product barcode
- `quantity`: Amount consumed (default: 1 serving)
- `meal_type`: Type of meal (breakfast, lunch, dinner, snack)

### 7. `get_user_food_log`

Get a user's food log for a specific date.

**Parameters:**
- `user_id`: The user's unique identifier
- `date`: Date in YYYY-MM-DD format (defaults to today)

## Example Usage Scenarios

### Setting Up a New User with Restrictions

1. Add a gluten allergy:
```
manage_user_restrictions(
    user_id="user123",
    action="add",
    restriction_type="allergen", 
    restriction_value="gluten",
    severity="avoid",
    notes="Avoid all wheat products"
)
```

2. Add a vegetarian diet:
```
manage_user_restrictions(
    user_id="user123",
    action="add",
    restriction_type="diet", 
    restriction_value="vegetarian"
)
```

### Tracking Food Consumption

1. Scan a product and log it:
```
# First get product info
product = get_product_by_barcode(barcode="3270190119357")

# Then log consumption
log_food_consumption(
    user_id="user123",
    barcode="3270190119357",
    quantity=1,
    meal_type="breakfast"
)
```

2. Check compatibility with restrictions:
```
check_product_compatibility(
    user_id="user123",
    barcode="3270190119357"
)
```

### Analyzing Nutritional Information

1. Get detailed nutrition analysis:
```
analyze_nutrition(barcode="3270190119357")
```

2. View food log and nutrition totals:
```
get_user_food_log(user_id="user123")
```

## Data Storage

The Food Tracker MCP stores data locally in JSON files:

- User profiles: `./data/users/{user_id}.json`
- Food logs: `./data/logs/{user_id}_{date}.json`

## Extending the MCP

You can extend the MCP by:

1. Adding new nutritional analysis features
2. Implementing more detailed diet plans and goals
3. Adding recipe suggestions based on available ingredients
4. Creating reports and visualizations of nutrition data
5. Implementing social features for sharing progress

## Troubleshooting

- If you encounter connection issues, ensure you have internet access as the MCP connects to the OpenFoodFacts API
- If product information is incomplete, this may be due to limitations in the OpenFoodFacts database
- For any data persistence issues, check the permissions on the data directory
