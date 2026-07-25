"""
商品批量导入路由
提供模板下载、预览校验、确认导入三个端点
"""
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO

from app.database import get_db
from app.services.import_service import (
    generate_template,
    parse_excel,
    preview_import,
    batch_import,
)

router = APIRouter(prefix="/api/v1/import", tags=["数据导入"])


@router.get("/products/template")
async def download_product_template():
    """Download product import Excel template."""
    content = generate_template()
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=商品导入模板.xlsx"},
    )


@router.post("/products/preview")
async def preview_products_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload Excel file and return preview validation results."""
    content = await file.read()
    rows = parse_excel(content)

    if not rows:
        return {
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "rows": [],
            "message": "文件中未找到有效数据，请检查表头是否正确",
        }

    preview_rows = preview_import(rows)
    return {
        "total_rows": len(preview_rows),
        "valid_count": sum(1 for r in preview_rows if r["valid"]),
        "invalid_count": sum(1 for r in preview_rows if not r["valid"]),
        "rows": preview_rows,
    }


@router.post("/products/confirm")
async def confirm_products_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Confirm import: upload same Excel file, execute batch write."""
    content = await file.read()
    rows = parse_excel(content)

    if not rows:
        return {
            "total": 0,
            "success": 0,
            "failed": [],
            "message": "文件中未找到有效数据",
        }

    result = batch_import(db, rows)
    return result
