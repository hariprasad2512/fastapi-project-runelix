import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .database import get_db
from .importer import clean_xlsx
from .models import Product, Supplier
from .schemas import ProductCreate, ProductResponse, ProductUpdate


logger = logging.getLogger(__name__)
router = APIRouter()


def product_query():
    return select(Product).options(joinedload(Product.supplier))


def get_supplier(db: Session, name: str, email: str) -> Supplier:
    supplier = db.scalar(select(Supplier).where(Supplier.email == email))
    if supplier is None:
        supplier = Supplier(name=name, email=email)
        db.add(supplier)
        db.flush()
    else:
        supplier.name = name
    return supplier


def product_from_record(db: Session, record: dict[str, str]) -> Product:
    supplier = get_supplier(db, record["Supplier Name"], record["Supplier Email"])
    return Product(
        name=record["Product Name"],
        category=record["Category"],
        price=Decimal(record["Price"]),
        quantity=Decimal(record["Quantity"]),
        supplier=supplier,
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_xlsx(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Upload an .xlsx file")

    try:
        result = clean_xlsx(file.file.read())
        existing_names = set(db.scalars(select(Product.name)).all())
        seen_names = set(existing_names)
        inserted = 0
        duplicate_records = []
        for record in result.valid_records:
            name = record["Product Name"]
            if name in seen_names:
                duplicate_records.append({"product_name": name, "reason": "duplicate product name"})
                logger.warning("Skipping duplicate product: %s", name)
                continue
            db.add(product_from_record(db, record))
            seen_names.add(name)
            inserted += 1
        db.commit()
        logger.info("Uploaded %s: inserted %s product(s), skipped %s row(s)", file.filename, inserted, len(result.skipped_records) + len(duplicate_records))
        return {"filename": file.filename, "inserted": inserted, "skipped": result.skipped_records + duplicate_records}
    except ValueError as error:
        db.rollback()
        logger.error("Validation failed for %s: %s", file.filename, error)
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        db.rollback()
        logger.exception("Import failed for %s", file.filename)
        raise HTTPException(status_code=500, detail="Could not import the workbook") from error


@router.get("/products", response_model=list[ProductResponse])
def get_all_products(db: Session = Depends(get_db)):
    return db.scalars(product_query().order_by(Product.id)).unique().all()


@router.get("/products/category/{category}", response_model=list[ProductResponse])
def get_product_by_category(category: str, db: Session = Depends(get_db)):
    return db.scalars(product_query().where(Product.category == category).order_by(Product.id)).unique().all()


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    product = db.scalar(product_query().where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/product", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Product).where(Product.name == product_data.name)):
        raise HTTPException(status_code=409, detail="Product name already exists")
    product = Product(
        name=product_data.name,
        category=product_data.category,
        price=product_data.price,
        quantity=product_data.quantity,
        supplier=get_supplier(db, product_data.supplier_name, str(product_data.supplier_email)),
    )
    db.add(product)
    try:
        db.commit()
        db.refresh(product)
        logger.info("Inserted product %s", product.id)
        return db.scalar(product_query().where(Product.id == product.id))
    except IntegrityError as error:
        db.rollback()
        logger.exception("Product insertion failed")
        raise HTTPException(status_code=409, detail="Product could not be inserted") from error


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product_details(product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = product_data.model_dump(exclude_unset=True)
    supplier_name = updates.pop("supplier_name", None)
    supplier_email = updates.pop("supplier_email", None)
    if "name" in updates and db.scalar(select(Product).where(Product.name == updates["name"], Product.id != product_id)):
        raise HTTPException(status_code=409, detail="Product name already exists")
    if supplier_name is not None or supplier_email is not None:
        supplier = product.supplier
        product.supplier = get_supplier(db, supplier_name or supplier.name, supplier_email or supplier.email)
    for field, value in updates.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return db.scalar(product_query().where(Product.id == product.id))


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    logger.info("Deleted product %s", product_id)
    return {"message": "Product deleted", "id": product_id}
