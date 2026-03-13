
"""
Check your Polymarket balance and open positions.
Run: python check_balance.py
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    print("[!] Install dotenv: pip install python-dotenv")
    sys.exit(1)

try:
    from py_clob_client.client import ClobClient
except:
    print("[!] Install clob client: pip install py-clob-client")
    sys.exit(1)

PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
FUNDER = os.getenv("FUNDER_ADDRESS", "")

# prevent crash if SIGNATURE_TYPE invalid
try:
    SIG_TYPE = int(os.getenv("SIGNATURE_TYPE", "1"))
except:
    SIG_TYPE = 1

if not PRIVATE_KEY or not FUNDER:
    print("ERROR: Missing PRIVATE_KEY or FUNDER_ADDRESS in .env file")
    sys.exit(1)

print("=" * 50)
print("  POLYMARKET BALANCE CHECKER")
print("=" * 50)
print()
print(f"  Funder: {FUNDER[:10]}...{FUNDER[-6:]}")
print()

try:
    client = ClobClient(
        "https://clob.polymarket.com",
        key=PRIVATE_KEY,
        chain_id=137,
        signature_type=SIG_TYPE,
        funder=FUNDER,
    )
    client.set_api_creds(client.create_or_derive_api_creds())
    print("[OK] Connected to Polymarket")
    print()

    # Balance
    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
        bal = client.get_balance_allowance(
            BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        if bal:
            print(f"  USDC BALANCE: ${float(bal.get('balance', 0)) / 1e6:.2f}")
            print(f"  Allowance:    ${float(bal.get('allowance', 0)) / 1e6:.2f}")
        else:
            print(f"  Balance response: {bal}")
    except Exception as e:
        try:
            import requests
            r = requests.get(
                "https://clob.polymarket.com/balance",
                headers=client.create_l2_headers(),
                timeout=10
            )
            print(f"  Balance: {r.json()}")
        except Exception as e2:
            print(f"  Balance error: {e}")
            print("  Try checking at: https://polymarket.com (top right)")

    print()

    # Open orders
    try:
        from py_clob_client.clob_types import OpenOrderParams
        orders = client.get_orders(OpenOrderParams())
        if orders:
            print(f"  OPEN ORDERS: {len(orders)}")
            for o in orders[:10]:
                print(f"    ID: {str(o.get('id', '?'))[:20]}  Side: {o.get('side', '?')}  Price: {o.get('price', '?')}  Size: {o.get('original_size', '?')}")
        else:
            print("  OPEN ORDERS: None")
    except Exception as e:
        print(f"  Orders: {e}")

    print()

    # Trade history
    try:
        from py_clob_client.clob_types import TradeParams
        trades = client.get_trades(TradeParams(trader=FUNDER))

        if trades:
            print(f"  RECENT TRADES: {len(trades)}")
            for t in trades[:5]:
                print(f"    Side: {t.get('side','?')}  Price: {t.get('price','?')}  Size: {t.get('size','?')}  Status: {t.get('status','?')}")
        else:
            print("  RECENT TRADES: None")
    except Exception as e:
        print(f"  Trades: {e}")

except Exception as e:
    print(f"[ERROR] {e}")

print()
print("=" * 50)
input("Press Enter to close...")
