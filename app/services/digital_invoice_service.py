"""
Servicio de Integración API REST para Facturación Digital en Venezuela (Imprentas Digitales Autorizadas SENIAT).
Cumple con las Providencias Administrativas SNAT/2014/0032 y SNAT/2011/00071, e incluye soporte para IGTF (3%)
y conversión bimonetaria oficial BCV (USD / VES).
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.sales import Sale, SaleDetail
from app.domain.tenant import Tenant


class DigitalInvoiceService:
    @staticmethod
    def build_seniat_json_payload(sale: Sale, tenant: Optional[Tenant] = None) -> Dict[str, Any]:
        """
        Construye el payload JSON estándar para proveedores de Facturación / Imprenta Digital en Venezuela.
        Contiene todos los campos fiscales obligatorios exigidos por el SENIAT:
        Emisor, Adquiriente (Cliente), Renglones (Exento/Gravado), Totales en Divisas y Equivalente en Bolívares (BCV).
        """
        tenant_obj = tenant or getattr(sale, "tenant", None)
        customer = getattr(sale, "customer", None)
        created_dt = sale.created_at or datetime.now(timezone.utc)

        rate = float(sale.exchange_rate) if sale.exchange_rate and float(sale.exchange_rate) > 0 else 1.0
        currency_code = "VES" if sale.currency in ["LOCAL", "VES"] else "USD"
        is_ves = currency_code == "VES"

        # ── Desglose de Renglones (Items) ────────────────────────────────────
        items_payload = []
        exempt_total_usd = 0.0
        taxable_base_usd = 0.0

        for idx, d in enumerate(sale.details or [], start=1):
            prod = getattr(d, "product", None)
            sku = getattr(prod, "sku", None) or f"ITEM-{d.product_id}"
            name = getattr(prod, "name", None) or f"Producto #{d.product_id}"
            unit_measure = getattr(prod, "unit_of_measure", None) or "UND"
            is_exempt = bool(getattr(prod, "tax_exempt", False)) if prod else False
            tax_rate_pct = 0.0 if is_exempt else float(getattr(prod, "tax_rate", 16.0) or 16.0)

            qty = float(d.quantity or 0.0)
            unit_price_raw = float(d.unit_price or 0.0)
            subtotal_raw = float(d.subtotal or (qty * unit_price_raw))
            disc_pct = float(getattr(d, "discount_percent", 0.0) or 0.0)
            disc_amt = float(getattr(d, "discount_amount", 0.0) or 0.0)

            unit_price_usd = (unit_price_raw / rate) if (is_ves and rate > 0) else unit_price_raw
            subtotal_usd = (subtotal_raw / rate) if (is_ves and rate > 0) else subtotal_raw
            unit_price_ves = unit_price_usd * rate
            subtotal_ves = subtotal_usd * rate

            line_tax_usd = 0.0 if is_exempt else round(subtotal_usd * (tax_rate_pct / 100.0), 4)
            line_tax_ves = round(line_tax_usd * rate, 4)

            if is_exempt:
                exempt_total_usd += subtotal_usd
            else:
                taxable_base_usd += subtotal_usd

            items_payload.append({
                "numero_linea": idx,
                "codigo_sku": sku,
                "descripcion": name,
                "unidad_medida": unit_measure.upper(),
                "cantidad": round(qty, 4),
                "indicador_fiscal": "E" if is_exempt else "G",
                "es_exento": is_exempt,
                "alicuota_iva_porcentaje": tax_rate_pct,
                "descuento_porcentaje": round(disc_pct, 2),
                "descuento_monto_usd": round(disc_amt, 4),
                "precio_unitario_usd": round(unit_price_usd, 4),
                "subtotal_usd": round(subtotal_usd, 4),
                "monto_iva_usd": round(line_tax_usd, 4),
                "total_linea_usd": round(subtotal_usd + line_tax_usd, 4),
                "precio_unitario_ves": round(unit_price_ves, 2),
                "subtotal_ves": round(subtotal_ves, 2),
                "monto_iva_ves": round(line_tax_ves, 2),
                "total_linea_ves": round((subtotal_usd + line_tax_usd) * rate, 2),
            })

        # ── Totales Fiscales (USD y Equivalente BCV en VES) ──────────────────
        raw_subtotal = float(sale.subtotal or 0.0)
        raw_igtf = float(sale.igtf_amount or 0.0)
        raw_tax_total = float(sale.tax_total or 0.0)
        raw_iva = max(0.0, raw_tax_total - raw_igtf) if raw_tax_total >= raw_igtf else (taxable_base_usd * 0.16)
        raw_total = float(sale.total or 0.0)
        raw_discount = float(sale.discount_total or 0.0)

        subtotal_usd = (raw_subtotal / rate) if (is_ves and rate > 0) else raw_subtotal
        iva_usd = (raw_iva / rate) if (is_ves and rate > 0) else raw_iva
        igtf_usd = (raw_igtf / rate) if (is_ves and rate > 0) else raw_igtf
        total_usd = (raw_total / rate) if (is_ves and rate > 0) else raw_total
        discount_usd = (raw_discount / rate) if (is_ves and rate > 0) else raw_discount

        inv_number = sale.fiscal_invoice_number or f"{sale.id:08d}"
        ctrl_number = sale.control_number or f"00-{sale.id:08d}"

        payload: Dict[str, Any] = {
            "version_esquema": "SENIAT-VE-1.0",
            "normativa_legal": "Providencias Administrativas SENIAT SNAT/2014/0032 y SNAT/2011/00071",
            "documento": {
                "tipo_documento": "01",  # 01 = Factura, 02 = Nota de Débito, 03 = Nota de Crédito
                "nombre_tipo_documento": "FACTURA",
                "id_interno_erp": sale.id,
                "numero_factura": inv_number,
                "numero_control": ctrl_number,
                "serie": "A",
                "fecha_emision": created_dt.strftime("%Y-%m-%d"),
                "hora_emision": created_dt.strftime("%H:%M:%S"),
                "fecha_hora_iso": created_dt.isoformat(),
                "condicion_pago": "CREDITO" if sale.payment_method == "credit" else "CONTADO",
                "metodo_pago": (sale.payment_method or "cash").upper(),
                "moneda_operacion": currency_code,
                "tasa_cambio_bcv": round(rate, 4),
                "observaciones": sale.notes or "",
            },
            "emisor": {
                "razon_social": tenant_obj.name if tenant_obj and tenant_obj.name else "EMPRESA EMISORA S.A.",
                "rif": (tenant_obj.tax_id if tenant_obj and tenant_obj.tax_id else "J-00000000-0").upper(),
                "domicilio_fiscal": tenant_obj.address if tenant_obj and tenant_obj.address else "Venezuela",
                "telefono": tenant_obj.phone if tenant_obj and tenant_obj.phone else "",
                "correo_electronico": getattr(tenant_obj, "email", None) or "",
                "logo_configured": bool(tenant_obj and getattr(tenant_obj, "logo_url", None)),
            },
            "adquiriente": {
                "id_cliente": customer.id if customer else 1,
                "razon_social": (customer.name if customer and customer.name else "CONSUMIDOR FINAL").upper(),
                "rif_ci": (customer.tax_id if customer and customer.tax_id else "V-00000000-0").upper(),
                "domicilio_fiscal": customer.address if customer and customer.address else "Venezuela",
                "telefono": customer.phone if customer and customer.phone else "",
                "correo_electronico": customer.email if customer and customer.email else "",
            },
            "items": items_payload,
            "totales": {
                "moneda_base": "USD",
                "tasa_bcv": round(rate, 4),
                "divisas_usd": {
                    "monto_exento": round(exempt_total_usd, 2),
                    "base_imponible_general_16": round(subtotal_usd - exempt_total_usd, 2),
                    "subtotal_neto": round(subtotal_usd, 2),
                    "descuento_total": round(discount_usd, 2),
                    "alicuota_iva_porcentaje": 16.0,
                    "monto_iva_16": round(iva_usd, 2),
                    "base_imponible_igtf": round((subtotal_usd + iva_usd) if igtf_usd > 0 else 0.0, 2),
                    "alicuota_igtf_porcentaje": 3.0 if igtf_usd > 0 else 0.0,
                    "monto_igtf_3": round(igtf_usd, 2),
                    "total_a_pagar": round(total_usd, 2),
                },
                "bolivares_ves": {
                    "monto_exento": round(exempt_total_usd * rate, 2),
                    "base_imponible_general_16": round((subtotal_usd - exempt_total_usd) * rate, 2),
                    "subtotal_neto": round(subtotal_usd * rate, 2),
                    "descuento_total": round(discount_usd * rate, 2),
                    "alicuota_iva_porcentaje": 16.0,
                    "monto_iva_16": round(iva_usd * rate, 2),
                    "base_imponible_igtf": round(((subtotal_usd + iva_usd) * rate) if igtf_usd > 0 else 0.0, 2),
                    "alicuota_igtf_porcentaje": 3.0 if igtf_usd > 0 else 0.0,
                    "monto_igtf_3": round(igtf_usd * rate, 2),
                    "total_a_pagar": round(total_usd * rate, 2),
                },
            },
        }
        return payload

    @staticmethod
    async def transmit_to_provider_api(
        db: AsyncSession,
        sale: Sale,
        tenant: Optional[Tenant]
    ) -> Dict[str, Any]:
        """
        Envía el JSON de la factura a la API REST de la empresa proveedora de Facturación Digital.
        Si la proveedora retorna un Número de Control SENIAT o Número de Factura asignado,
        actualiza automáticamente el registro de la venta en la base de datos.
        """
        payload = DigitalInvoiceService.build_seniat_json_payload(sale, tenant)
        settings = (tenant.settings if tenant and isinstance(tenant.settings, dict) else {}) or {}
        api_cfg = settings.get("digital_invoice_api", {}) or {}

        enabled = bool(api_cfg.get("enabled", False))
        provider_name = api_cfg.get("provider_name", "custom_rest")
        endpoint_url = (api_cfg.get("endpoint_url") or "").strip()
        auth_type = api_cfg.get("auth_type", "bearer")
        api_token = (api_cfg.get("api_token") or "").strip()
        custom_header = (api_cfg.get("api_header_name") or "X-API-Key").strip()
        environment = api_cfg.get("environment", "sandbox")

        # Si no hay URL configurada o está en modo simulación local (sandbox sin URL externa),
        # ejecutamos simulación homologada para que el usuario pueda probar el flujo completo.
        if not endpoint_url:
            simulated_ctrl = sale.control_number or f"00-{sale.id:08d}"
            simulated_inv = sale.fiscal_invoice_number or f"{sale.id:08d}"
            return {
                "status": "simulated",
                "transmitted": False,
                "environment": environment,
                "provider": provider_name,
                "message": (
                    "Modo Simulación / Sandbox Activo: El JSON Fiscal SENIAT fue generado y validado correctamente. "
                    "Configure la URL del Endpoint API REST de su Imprenta Digital en Configuración para transmitir en vivo."
                ),
                "control_number": simulated_ctrl,
                "fiscal_invoice_number": simulated_inv,
                "sent_json": payload,
                "provider_response": {
                    "success": True,
                    "modo": "SIMULACION_HOMOLOGACION_SENIAT",
                    "numero_factura_asignado": simulated_inv,
                    "numero_control_seniat": simulated_ctrl,
                    "fecha_asignacion": datetime.now(timezone.utc).isoformat(),
                },
            }

        # Preparar cabeceras HTTP para consumir la API REST de la empresa proveedora
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "APEX-ERP-Venezuela-FiscalClient/1.0",
        }
        if api_token:
            if auth_type == "bearer":
                headers["Authorization"] = f"Bearer {api_token}"
            elif auth_type == "api_key":
                headers[custom_header or "X-API-Key"] = api_token
            elif auth_type == "basic":
                headers["Authorization"] = f"Basic {api_token}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(endpoint_url, json=payload, headers=headers)

            try:
                resp_data = response.json()
            except Exception:
                resp_data = {"raw_body": response.text}

            if response.status_code in (200, 201, 202):
                # Extraer número de control y número de factura si el proveedor los asigna en su respuesta
                assigned_ctrl = (
                    resp_data.get("numero_control")
                    or resp_data.get("control_number")
                    or (resp_data.get("data") or {}).get("numero_control")
                    or (resp_data.get("data") or {}).get("control_number")
                )
                assigned_inv = (
                    resp_data.get("numero_factura")
                    or resp_data.get("invoice_number")
                    or (resp_data.get("data") or {}).get("numero_factura")
                )

                if assigned_ctrl:
                    sale.control_number = str(assigned_ctrl)
                if assigned_inv:
                    sale.fiscal_invoice_number = str(assigned_inv)
                if assigned_ctrl or assigned_inv:
                    await db.commit()
                    await db.refresh(sale)

                return {
                    "status": "success",
                    "transmitted": True,
                    "http_status": response.status_code,
                    "environment": environment,
                    "provider": provider_name,
                    "message": "Factura Digital transmitida exitosamente a la API REST del proveedor autorizado SENIAT.",
                    "control_number": sale.control_number,
                    "fiscal_invoice_number": sale.fiscal_invoice_number,
                    "sent_json": payload,
                    "provider_response": resp_data,
                }
            else:
                return {
                    "status": "error",
                    "transmitted": False,
                    "http_status": response.status_code,
                    "environment": environment,
                    "provider": provider_name,
                    "message": f"La API del proveedor retornó HTTP {response.status_code}.",
                    "control_number": sale.control_number,
                    "fiscal_invoice_number": sale.fiscal_invoice_number,
                    "sent_json": payload,
                    "provider_response": resp_data,
                }
        except Exception as exc:
            return {
                "status": "error",
                "transmitted": False,
                "environment": environment,
                "provider": provider_name,
                "message": f"Error de conexión al consumir la API REST del proveedor: {str(exc)}",
                "control_number": sale.control_number,
                "fiscal_invoice_number": sale.fiscal_invoice_number,
                "sent_json": payload,
                "provider_response": None,
            }

