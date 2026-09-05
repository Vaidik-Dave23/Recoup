from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
import razorpay

from app.core.config import settings

router = APIRouter(
    tags=["Checkout"],
)


def _client() -> razorpay.Client:
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


@router.get("/checkout-info/{order_id}")
async def get_checkout_info(order_id: str):
    """Public endpoint to fetch order details for the hosted Razorpay checkout page."""
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay is not configured",
        )

    try:
        c = _client()
        if order_id.startswith("order_"):
            ord_data = c.order.fetch(order_id)
            notes = ord_data.get("notes") or {}
            # Also check if already paid
            amount_paid = ord_data.get("amount_paid", 0)
            is_paid = ord_data.get("status") == "paid" or (amount_paid and amount_paid > 0)
            
            return {
                "order_id": ord_data.get("id"),
                "amount": ord_data.get("amount"),
                "currency": ord_data.get("currency", "INR"),
                "status": "paid" if is_paid else ord_data.get("status", "created"),
                "amount_paid": amount_paid,
                "key_id": settings.razorpay_key_id,
                "receipt": ord_data.get("receipt"),
                "customer_name": notes.get("customer_name", "Customer"),
                "customer_email": notes.get("customer_email", ""),
                "description": notes.get("description", "Invoice Recovery Payment"),
            }
        else:
            link = c.payment_link.fetch(order_id)
            cust = link.get("customer") or {}
            return {
                "order_id": link.get("id"),
                "amount": link.get("amount"),
                "currency": link.get("currency", "INR"),
                "status": link.get("status", "created"),
                "amount_paid": link.get("amount_paid", 0),
                "key_id": settings.razorpay_key_id,
                "receipt": link.get("reference_id"),
                "customer_name": cust.get("name", "Customer"),
                "customer_email": cust.get("email", ""),
                "description": link.get("description", "Invoice Recovery Payment"),
            }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order/Link not found on Razorpay: {exc}",
        )


@router.get("/pay/{order_id}", response_class=HTMLResponse)
async def hosted_pay_page(order_id: str):
    """Standalone Razorpay Test Mode checkout page that can be opened anywhere."""
    try:
        c = _client()
        ord_data = c.order.fetch(order_id)
        amount = ord_data.get("amount", 0)
        currency = ord_data.get("currency", "INR")
        notes = ord_data.get("notes") or {}
        cust_name = notes.get("customer_name", "Valued Customer")
        cust_email = notes.get("customer_email", "")
        desc = notes.get("description", "Invoice Recovery Payment")
        key_id = settings.razorpay_key_id
        amount_fmt = f"{currency} {amount / 100:.2f}"
    except Exception:
        amount_fmt = "Payment"
        key_id = settings.razorpay_key_id
        cust_name = "Customer"
        cust_email = ""
        desc = "Invoice Recovery Payment"
        amount = 50000
        currency = "INR"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Recoup Secure Payment Recovery</title>
  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <style>
    :root {{
      --bg: #090d16;
      --card: #111827;
      --border: #1f2937;
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --success: #10b981;
      --text: #f3f4f6;
      --muted: #9ca3af;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    body {{
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .checkout-card {{
      background-color: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 32px;
      max-width: 460px;
      width: 100%;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
      text-align: center;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.3);
      color: #818cf8;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 16px;
    }}
    .title {{ font-size: 20px; font-weight: 700; margin-bottom: 8px; color: #fff; }}
    .subtitle {{ font-size: 13px; color: var(--muted); margin-bottom: 24px; }}
    .amount-box {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;
    }}
    .amount-label {{ font-size: 12px; color: var(--muted); margin-bottom: 4px; text-transform: uppercase; }}
    .amount-value {{ font-size: 30px; font-weight: 800; color: #fff; }}
    .details-row {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      padding: 8px 0;
      border-bottom: 1px solid #1e293b;
    }}
    .details-row:last-child {{ border-bottom: none; }}
    .btn {{
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 14px 24px;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
      margin-top: 24px;
      transition: background 0.2s, transform 0.1s;
    }}
    .btn:hover {{ background: var(--primary-hover); transform: translateY(-1px); }}
    .btn:active {{ transform: translateY(0); }}
    .footer-note {{ font-size: 11px; color: var(--muted); margin-top: 16px; }}
    .success-container {{ display: none; margin-top: 10px; }}
    .success-icon {{ font-size: 48px; color: var(--success); margin-bottom: 12px; }}
  </style>
</head>
<body>
  <div class="checkout-card" id="card">
    <span class="badge">Razorpay Test Mode</span>
    <h1 class="title">Complete Payment</h1>
    <p class="subtitle">{desc}</p>
    
    <div class="amount-box">
      <div class="amount-label">Amount Due</div>
      <div class="amount-value">{amount_fmt}</div>
    </div>

    <div style="margin-bottom: 12px; text-align: left;">
      <div class="details-row">
        <span style="color: var(--muted);">Order ID:</span>
        <span style="font-family: monospace; font-size: 12px;">{order_id}</span>
      </div>
      <div class="details-row">
        <span style="color: var(--muted);">Customer:</span>
        <span>{cust_name}</span>
      </div>
      {f'<div class="details-row"><span style="color: var(--muted);">Email:</span><span>{cust_email}</span></div>' if cust_email else ''}
    </div>

    <button id="pay-btn" class="btn" onclick="openRazorpay()">Pay with Razorpay (Test Mode)</button>

    <div id="success-view" class="success-container">
      <div class="success-icon">✓</div>
      <h2 style="font-size: 18px; color: var(--success); margin-bottom: 8px;">Payment Successful!</h2>
      <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">
        Your payment has been authorized in Test Mode. Recoup autonomous recovery system has detected and synced this invoice.
      </p>
      <div style="background: #064e3b; border: 1px solid #059669; border-radius: 6px; padding: 10px; font-size: 12px; color: #a7f3d0;" id="payment-ref">
        Payment Confirmed
      </div>
    </div>

    <p class="footer-note">⚡ Secured by Razorpay Payment Gateway (Test Environment)</p>
  </div>

  <script>
    var options = {{
      "key": "{key_id}",
      "amount": {amount},
      "currency": "{currency}",
      "name": "Recoup Recovery",
      "description": "{desc}",
      "order_id": "{order_id}",
      "prefill": {{
        "name": "{cust_name}",
        "email": "{cust_email}"
      }},
      "theme": {{
        "color": "#6366f1"
      }},
      "handler": function (response) {{
        document.getElementById('pay-btn').style.display = 'none';
        document.getElementById('success-view').style.display = 'block';
        document.getElementById('payment-ref').innerText = "Razorpay Payment ID: " + response.razorpay_payment_id;
      }}
    }};

    function openRazorpay() {{
      if (typeof Razorpay === 'undefined') {{
        alert('Razorpay Checkout SDK is still loading. Please try again in 1 second.');
        return;
      }}
      var rzp = new Razorpay(options);
      rzp.on('payment.failed', function (response) {{
        alert('Payment Failed: ' + response.error.description);
      }});
      rzp.open();
    }}

    // Automatically trigger Razorpay checkout modal on load
    window.addEventListener('load', function() {{
      setTimeout(function() {{
        openRazorpay();
      }}, 600);
    }});
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
