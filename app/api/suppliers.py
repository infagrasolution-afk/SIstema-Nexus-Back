from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db, get_current_tenant
from app.domain.purchases import Supplier
from app.schemas.suppliers import SupplierCreate, SupplierResponse, SupplierUpdate

router = APIRouter()

@router.get("/", response_model=List[SupplierResponse])
async def get_suppliers(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Supplier).where(Supplier.tenant_id == tenant_id))
    return result.scalars().all()

@router.post("/", response_model=SupplierResponse)
async def create_supplier(
    supplier_in: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    new_supplier = Supplier(**supplier_in.model_dump(), tenant_id=tenant_id)
    db.add(new_supplier)
    await db.commit()
    await db.refresh(new_supplier)
    return new_supplier

@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
    )
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    supplier_in: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
    )
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)
        
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.post("/import")
async def import_suppliers_bulk(
    suppliers_in: List[SupplierCreate],
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    imported_count = 0
    errors = []
    
    for idx, s_in in enumerate(suppliers_in):
        if not s_in.tax_id or not s_in.name:
            errors.append(f"Fila {idx+1}: Nombre y RIF son campos obligatorios.")
            continue
            
        # Check if already exists by tax_id
        check_stmt = select(Supplier).where(Supplier.tax_id == s_in.tax_id, Supplier.tenant_id == tenant_id)
        res = await db.execute(check_stmt)
        existing = res.scalars().first()
        
        if existing:
            # Update existing
            for field, value in s_in.model_dump().items():
                if value is not None:
                    setattr(existing, field, value)
        else:
            # Create new
            new_s = Supplier(**s_in.model_dump(), tenant_id=tenant_id)
            db.add(new_s)
            
        imported_count += 1
        
    await db.commit()
    return {"status": "success", "imported": imported_count, "errors": errors}

