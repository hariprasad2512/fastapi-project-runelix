# Runelix Product API

A FastAPI service for importing product data from XLSX files into PostgreSQL and managing products through REST APIs.

## Requirements

- Python 3.10 or newer
- PostgreSQL running locally or on a server
- A PostgreSQL database named `runelix` (or another database named in `DATABASE_URL`)

## Installation

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root. It is ignored by Git because it may contain credentials.

For the local PostgreSQL setup using the current OS user:

```env
DATABASE_URL=postgresql+psycopg2:///runelix
```

For a PostgreSQL server requiring a username and password:

```env
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/runelix
```

The application accepts only PostgreSQL connection URLs. Do not commit `.env` or real credentials.

## Run the API

```bash
uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

Interactive API documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

At startup, the application creates the `products` and `suppliers` tables. If it finds the old empty tables created with the original Excel column names, it replaces them with the current schema. It refuses to remove a legacy table that contains data.

## XLSX Upload

Upload an `.xlsx` file using Swagger UI or curl:

```bash
curl -X POST \
	http://127.0.0.1:8000/upload \
	-H "accept: application/json" \
	-F "file=@sample_products_validation.xlsx"
```

The first worksheet must contain these columns:

```text
Product Name
Category
Price
Quantity
Supplier Name
Supplier Email
```

Rows with missing mandatory values, invalid email addresses, or invalid numeric values are skipped and logged. Products with duplicate names are also skipped. Valid rows are stored in both tables inside one database transaction.

Example response:

```json
{
	"filename": "products.xlsx",
	"inserted": 3,
	"skipped": []
}
```

## REST Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Health message |
| `POST` | `/upload` | Validate and import an XLSX file |
| `GET` | `/products` | Return all products |
| `GET` | `/products/{product_id}` | Return one product |
| `GET` | `/products/category/{category}` | Filter products by category |
| `POST` | `/product` | Create a product |
| `PUT` | `/products/{product_id}` | Update a product |
| `DELETE` | `/products/{product_id}` | Delete a product |

## Project Structure

```text
.
├── app/
│   ├── api.py          # API routes and database operations
│   ├── database.py     # PostgreSQL engine, sessions, and startup schema setup
│   ├── importer.py     # XLSX parsing and validation
│   ├── models.py       # SQLAlchemy database models
│   └── schemas.py      # Pydantic request and response schemas
├── clean_data.py       # Optional CSV cleaning utility
├── main.py             # FastAPI application entry point
├── requirements.txt
└── .env                # Local configuration, not committed
```

## Logging and Errors

The service logs API requests, validation failures, skipped records, duplicate products, successful inserts, deletions, and application errors. Database changes are rolled back when an import or write operation fails.
